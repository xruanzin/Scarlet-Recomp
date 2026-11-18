// Horizon csrng: IRandomInterface::GetRandomBytes (cmd 0).
// The request carries the destination as an output map-alias (B) or
// auto-select (C) buffer; its inline input payload is normally empty.
// Never acknowledge a request without actually filling its buffer.
// Source bytes from the operating system's CSPRNG, not rand()/time().
#include <stdint.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif

#include "../hle.h"
#include "../ipc.h"

static int os_random_bytes(void *dst, size_t len) {
#ifdef _WIN32
    // bcrypt.h uses NTSTATUS; a negative status indicates failure.
    return BCryptGenRandom(NULL, (PUCHAR)dst, (ULONG)len,
                           BCRYPT_USE_SYSTEM_PREFERRED_RNG) >= 0;
#else
    // /dev/urandom is the OS CSPRNG; handle short reads and signals.
    int fd = open("/dev/urandom", O_RDONLY);
    if (fd < 0) return 0;
    unsigned char *p = dst;
    size_t remaining = len;
    while (remaining) {
        ssize_t n = read(fd, p, remaining);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { close(fd); return 0; }
        p += n;
        remaining -= (size_t)n;
    }
    close(fd);
    return 1;
#endif
}

SERVICE("csrng", csrng) {
    (void)s;
    if (req->cmd != 0) {
        LOG("[csrng] unsupported command %u\n", req->cmd);
        resp->result = MAKE_RESULT(1, 1);
        return;
    }

    IpcBuf *out = out_buf(req, 0);
    // Prevent missing or corrupt IPC descriptors from being reported as
    // successful RNG requests. Normal SDK calls use the B output buffer.
    if (!out || (out->size && !out->addr) || out->size > (16ull << 20)) {
        LOG("[csrng] invalid output buffer (B=%d C=%d)\n", req->nb, req->nc);
        resp->result = MAKE_RESULT(1, 1);
        return;
    }
    if (out->size && !os_random_bytes((void *)(uintptr_t)out->addr, (size_t)out->size)) {
        LOG("[csrng] operating system entropy request failed (size=%llu)\n",
            (unsigned long long)out->size);
        resp->result = MAKE_RESULT(1, 1);
        return;
    }
    static unsigned reported;
    if (reported++ < 3)
        LOG("[csrng] filled %llu random bytes using OS CSPRNG\n",
            (unsigned long long)out->size);
}
