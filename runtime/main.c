// LAS Recomp entry: load modules, set up the kernel, run nn::init::Start on the main thread.
#include <SDL3/SDL.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "game_addresses.h"
#include "gamelib.h"
#include "paths.h"
#include "settings.h"
#include "hle.h"
#include "kernel.h"
#include "rando.h"
#include "platform.h"
#include "gamebuild.h"  // (gamelib_old_cpu)
#include <stdio.h>
#if defined(SCARLET_AOT) && defined(_WIN32)
#include <windows.h>
#include <wchar.h>
// Exact Scarlet PC native Win32/GDI+ launcher lives next to scarlet.exe.
// Spawn it on normal double-click BEFORE initializing any game/Vulkan state.
static int scarlet_launch_original_ui(void) {
    wchar_t program[4096] = {};
    DWORD n = GetModuleFileNameW(NULL, program, (DWORD)(sizeof program / sizeof program[0]));
    if (!n || n >= (DWORD)(sizeof program / sizeof program[0] - 32)) return 4;
    wchar_t *sep = wcsrchr(program, L'\\');
    if (!sep) return 4;
    wcscpy(sep + 1, L"ScarletLauncher.exe");
    STARTUPINFOW si = {0};
    PROCESS_INFORMATION pi = {0};
    si.cb = sizeof si;
    if (!CreateProcessW(program, NULL, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi)) {
        MessageBoxW(NULL,
            L"ScarletLauncher.exe não encontrado. Compile o launcher nativo.",
            L"Scarlet", MB_OK | MB_ICONERROR);
        return 4;
    }
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return 0;
}
#endif
#if defined(__x86_64__) || defined(__i386__)
#include <cpuid.h>
#endif
#ifdef __APPLE__
#include <sys/sysctl.h>
#endif

const char *g_romfs_dir;

// The player's machine at the top of the log: what a slow or broken run report needs first (the CPU runs the
// recompiled game code; the GPU line comes from runtime/nvn/vulkan/device.c). No user or machine names, no paths.
static void cpu_name(char *buf, size_t size) {
    snprintf(buf, size, "unknown CPU");
#if defined(__x86_64__) || defined(__i386__)
    unsigned r[12], top = __get_cpuid_max(0x80000000, NULL);
    if (top >= 0x80000004) {
        for (unsigned i = 0; i < 3; i++) __get_cpuid(0x80000002 + i, &r[4 * i], &r[4 * i + 1], &r[4 * i + 2], &r[4 * i + 3]);
        char s[49];
        memcpy(s, r, 48);
        s[48] = 0;
        char *p = s;
        while (*p == ' ') p++;
        snprintf(buf, size, "%s", p);
    }
#elif defined(__APPLE__)
    size_t n = size;
    if (sysctlbyname("machdep.cpu.brand_string", buf, &n, NULL, 0) != 0) snprintf(buf, size, "Apple CPU");
#else
    FILE *f = fopen("/proc/cpuinfo", "r");
    char line[256];
    while (f && fgets(line, sizeof line, f))
        if (!strncmp(line, "model name", 10) || !strncmp(line, "Model", 5)) {
            char *v = strchr(line, ':');
            if (v) { v += 1 + (v[1] == ' '); v[strcspn(v, "\n")] = 0; snprintf(buf, size, "%s", v); break; }
        }
    if (f) fclose(f);
#endif
}
static void log_system(void) {
    extern const char *rt_version(void);  // runtime/ui/launcher.mm
    char cpu[128], os[160];
    cpu_name(cpu, sizeof cpu);
    plat_os_name(os, sizeof os);
    char feat[96] = "";
#if defined(__x86_64__)
    snprintf(feat, sizeof feat, ", AVX2 %s FMA %s BMI2 %s -> game code for x86-64-%s",
             __builtin_cpu_supports("avx2") ? "yes" : "no", __builtin_cpu_supports("fma") ? "yes" : "no",
             __builtin_cpu_supports("bmi2") ? "yes" : "no", gamelib_old_cpu() ? "v2" : "v3");
#endif
    LOG("[system] ZA Recomp %s | %s | CPU: %s (%d threads%s) | RAM %d GB\n", rt_version(), os, cpu,
        SDL_GetNumLogicalCPUCores(), feat, (SDL_GetSystemRAM() + 512) / 1024);
#ifdef _WIN32
    plat_run_begin();
#endif
}

// rtld normally passes these to nn::init::Start: run every module's init/fini arrays.
static void run_array(Cpu *c, uint64_t arr, uint64_t size) {
    for (uint64_t i = 0; i < size / 8; i++) {
        uint64_t fn = ((uint64_t *)arr)[i];
        if (fn) guest_call(c, fn);
    }
}

// nn::init::Start calls x2 right after nnosInitialize and x3 after nninitStartup, just before
// nnMain: SDK constructors run early, the game's run once nninitStartup has set up its heap.
// rtld runs a module's DT_INIT, which registers it (and its TLS template) with musl via
// __nnmusl_init_dso and then runs its init_array; fall back to the array if there is no DT_INIT.
static void module_init(Cpu *c, Module *m) {
    LOG("init %s (DT_INIT %llx, %llu init_array entries)\n", m->name, m->init, m->init_array_sz / 8);
    if (m->init) guest_call(c, m->init);
    else run_array(c, m->init_array, m->init_array_sz);
}

// Scarlet 4.0.0's SDK DT_INIT can call the main module's malloc before
// the SDK has installed TPIDR_EL0. The allocator reads TPIDR_EL0+0x30.
// An opt-in, guest-mapped bootstrap area allows investigating that early call
// without mutating the AOT modules or faking the TLR's SDK ThreadPointer slot.
// The SDK is still responsible for creating its real per-thread TLS object.
static void scarlet_early_tls_probe(Cpu *c) {
    if (g_program_id != 0x0100a3d008c5c000ull) return;
    const char *opt = getenv("SCARLET_EARLY_TLS_PROBE");
    if (!opt || !*opt || !strcmp(opt, "0")) return;
    uint64_t known = c->tpidrro ? *(uint64_t *)(uintptr_t)(c->tpidrro + 0x1f0) : 0;
    LOG("[scarlet/tls] before SDK init: TPIDR=%llx TPIDRRO=%llx TLR.ThreadPointer=%llx\n",
        (unsigned long long)c->tpidr, (unsigned long long)c->tpidrro, (unsigned long long)known);
    if (!c->tpidr) {
        c->tpidr = known ? known : (uint64_t)(uintptr_t)hle_alloc(0x1000);
        LOG("[scarlet/tls] early TPIDR=%llx (%s); TLR.ThreadPointer left unchanged\n",
            (unsigned long long)c->tpidr, known ? "existing SDK pointer" : "temporary guest-mapped probe buffer");
    }
}
// Main's malloc (f_7002b7d830) dispatches via TLS[0x30], then invokes
// vtable[0x10] with (allocator, bytes, alignment) in x0/x1/x2.
// The optional diagnostic shim below implements ONLY this allocation slot.
// Unlike the earlier zeroed TLS probe, it returns real guest-mapped buffers.
// It does not implement free/realloc/heap ownership: never enable in release.
static void scarlet_bootstrap_allocate(Cpu *c) {
    uint64_t size = c->x[1], alignment = c->x[2];
    if (alignment < 8) alignment = 8;
    if (alignment > 65536 || (alignment & (alignment - 1)) || size > (16ull << 20))
        FATAL("[scarlet/bootstrap] unsupported early allocation size=%llu align=%llu\n",
            (unsigned long long)size, (unsigned long long)alignment);
    uintptr_t raw = (uintptr_t)hle_alloc(size + alignment - 1);
    c->x[0] = (uint64_t)((raw + alignment - 1) & ~(uintptr_t)(alignment - 1));
    static unsigned count;
    if (count++ < 20)
        LOG("[scarlet/bootstrap] alloc #%u size=%llu align=%llu result=%llx\n",
            count, (unsigned long long)size, (unsigned long long)alignment,
            (unsigned long long)c->x[0]);
}
static void scarlet_bootstrap_allocator_probe(Cpu *c) {
    if (g_program_id != 0x0100a3d008c5c000ull) return;
    const char *opt = getenv("SCARLET_BOOTSTRAP_ALLOCATOR");
    if (!opt || !*opt || !strcmp(opt, "0")) return;
    if (!c->tpidr) {
        LOG("[scarlet/bootstrap] no TPIDR: enable SCARLET_EARLY_TLS_PROBE=1\n");
        return;
    }
    uint64_t *slot = (uint64_t *)(uintptr_t)(c->tpidr + 0x30);
    if (*slot) {
        LOG("[scarlet/bootstrap] TLS already has allocator at %llx; not replacing\n",
            (unsigned long long)*slot);
        return;
    }
    uint64_t *vtable = hle_alloc(0x40);
    uint64_t *object = hle_alloc(0x40);
    vtable[2] = hle_register("<scarlet_bootstrap_allocate>", scarlet_bootstrap_allocate);
    object[0] = (uint64_t)(uintptr_t)vtable;
    *slot = (uint64_t)(uintptr_t)object;
    LOG("[scarlet/bootstrap] temporary TLS allocator: TPIDR=%llx object=%llx vtable=%llx callback=%llx\n",
        (unsigned long long)c->tpidr, (unsigned long long)*slot,
        (unsigned long long)object[0], (unsigned long long)vtable[2]);
}
// A separate opt-in A/B probe for the Scarlet v4.0.0 startup dependency:
 // main!malloc consults a guarded global allocator pointer at 0x7004759430,
 // loaded from 0x7004759418, before the SDK finishes its DT_INIT.
 // Log those observed guest addresses and, only when explicitly requested,
 // try running main's DT_INIT before the SDK's. This order is experimental:
 // the main initializer may itself depend on SDK initialization.
static bool scarlet_main_init_early;
static bool scarlet_probe_enabled(const char *name) {
    const char *v = getenv(name);
    return g_program_id == 0x0100a3d008c5c000ull && v && *v && strcmp(v, "0");
}
static void scarlet_allocator_probe(const char *when) {
    if (!scarlet_probe_enabled("SCARLET_MAIN_INIT_FIRST")) return;
    const uint64_t *seed = (const uint64_t *)(uintptr_t)0x7004759418ull;
    const uint64_t *instance = (const uint64_t *)(uintptr_t)0x7004759430ull;
    const uint8_t *guard = (const uint8_t *)(uintptr_t)0x7004759438ull;
    LOG("[scarlet/alloc] %s: backing=%llx singleton=%llx guard=%02x\n",
        when, (unsigned long long)*seed, (unsigned long long)*instance, (unsigned)*guard);
}
static void rtld_init_sdk(Cpu *c) {
    scarlet_early_tls_probe(c);
    scarlet_bootstrap_allocator_probe(c);
    if (scarlet_probe_enabled("SCARLET_MAIN_INIT_FIRST")) {
        LOG("[scarlet/init] EXPERIMENT: main DT_INIT before sdk DT_INIT (no double init)\n");
        scarlet_allocator_probe("before main DT_INIT");
        module_init(c, &g_modules[0]);
        scarlet_main_init_early = true;
        scarlet_allocator_probe("after main DT_INIT");
    }
    scarlet_allocator_probe("before sdk DT_INIT");
    module_init(c, &g_modules[1]);
    if (scarlet_probe_enabled("SCARLET_EARLY_TLS_PROBE"))
        LOG("[scarlet/tls] after SDK init: TPIDR=%llx TLR.ThreadPointer=%llx\n",
            (unsigned long long)c->tpidr,
            (unsigned long long)(c->tpidrro ? *(uint64_t *)(uintptr_t)(c->tpidrro + 0x1f0) : 0));
}
static void rtld_init_main(Cpu *c) {
    // Keep the original order by default; with the explicit Scarlet A/B
    // experiment, main DT_INIT already ran, so it must not run twice.
    for (int i = g_nmodules - 1; i >= 2; i--) module_init(c, &g_modules[i]);
    if (!scarlet_main_init_early) module_init(c, &g_modules[0]);
    else LOG("[scarlet/init] skipping main DT_INIT: already ran in first callback\n");
}
static void rtld_fini(Cpu *c) { (void)c; LOG("nnMain returned\n"); }

// Claim the guest address range before anything else can map there. The host allocator places
// regions at random addresses in the same window; on a collision, re-exec for a fresh layout.
// LARECOMP_REEXEC_FORCE=1 (test): the first process skips the reservation once and starts again, as when the range is
// taken (the new process has LARECOMP_REEXEC set and reserves normally).
#define REEXEC_FORCED "forced by LARECOMP_REEXEC_FORCE"
__attribute__((constructor(101))) static void reserve_guest_space(void) {
    const char *force = getenv("LARECOMP_REEXEC_FORCE");
    bool forced = force && *force && strcmp(force, "0") && !getenv("LARECOMP_REEXEC");
    if (forced) setenv("LARECOMP_REEXEC_WHY", REEXEC_FORCED, 1);
    else if (plat_reserve_guest(GUEST_LO, GUEST_HI)) return;
    else setenv("LARECOMP_REEXEC_WHY", "", 0);  // (the platform may have said what holds the range; else nothing more)
    const char *tries = getenv("LARECOMP_REEXEC");
    int n = tries ? atoi(tries) : 0;
    if (n >= 20) {
        fprintf(stderr, "FATAL: guest address range %llx-%llx is not free\n", GUEST_LO, GUEST_HI);
        exit(1);
    }
    char buf[16];
    snprintf(buf, sizeof buf, "%d", n + 1);
    setenv("LARECOMP_REEXEC", buf, 1);
    plat_exec(NULL);
    perror("re-exec");
    exit(1);
}

// ------------------------------------------------------------------ boot / in-place reboot
// Switching seeds (or vanilla) and going back to the start screen reboot the game inside this process: the window,
// GPU device, settings and shader caches stay. rt_request_reboot (menu, any thread) makes ui_run return on the
// main thread, which then: stops every guest thread (kernel_stop_threads: each unwinds at its next svc / HLE call /
// wait), resets the renderer (textures, address-keyed caches) and all per-boot host state (RT_ON_RESET hooks:
// services, HLE features, seed data, audio), empties the kernel, wipes guest memory, and boots again.
static _Atomic int g_reboot;
void rt_request_reboot(int kind) {
    LOG("[reboot] requested (%s)\n", kind == RT_REBOOT_TITLE ? "start screen" : "boot");
    g_reboot = kind;
}
int rt_reboot_requested(void) { return g_reboot; }

// LARECOMP_REBOOT_AT=<frame>:<seed | vanilla | title>[,...] (test): at that presented frame, switch to the seed /
// vanilla in place, or go back to the start screen (with LARECOMP_LAUNCHER_AUTOPLAY it plays the saved choice).
// Frames count on across reboots. Called by the presenter every frame.
void reboot_test_frame(uint64_t frame) {
    static const char *next;
    static int init;
    if (!init) { init = 1; next = getenv("LARECOMP_REBOOT_AT"); }
    long at;
    char what[128];
    if (!next || !*next || sscanf(next, "%ld:%127[^,]", &at, what) != 2 || (long)frame < at) return;
    next = strchr(next, ',');
    if (next) next++;
    if (!strcmp(what, "title")) { rt_request_reboot(RT_REBOOT_TITLE); return; }
    // (a test run: the next boot's seed without saving it - larecomp.ini is the player's choice)
    strlcpy(g_settings.rando_seed, strcmp(what, "vanilla") ? what : "", sizeof g_settings.rando_seed);
    unsetenv("LARECOMP_RANDO_SEED");
    rt_request_reboot(RT_REBOOT_GAME);
}

#ifdef __APPLE__
extern const ResetFn __start_resets[] __asm__("section$start$__DATA$__rt_reset");
extern const ResetFn __stop_resets[] __asm__("section$end$__DATA$__rt_reset");
#elif defined(__linux__)
extern const ResetFn __start_resets[], __stop_resets[];  // (ELF: defined by the linker)
#else
// PE/COFF: .rst$a < .rst$m (entries, hle.h) < .rst$z (the linker sorts by the text after '$')
__attribute__((section(".rst$a"), used)) static const ResetFn __start_resets[1];
__attribute__((section(".rst$z"), used)) static const ResetFn __stop_resets[1];
#endif

void backend_reset(void);             // renderer: GPU idle, game textures and address-keyed caches dropped
void backend_guest_memory_reset(void);  // renderer: guest memory was replaced (re-wrap the heap)
void backend_clear_window(void);      // a black frame while the game is down
void backend_quit(void);              // quitting: the render thread stopped, the GPU idle, caches kept (before exit())

static void reboot_idle(void) {  // (main thread, while guest threads stop) keep the window alive
    SDL_Event e;
    while (SDL_PollEvent(&e))
        if (e.type == SDL_EVENT_QUIT) { LOG("window closed\n"); backend_quit(); exit(0); }
}

static void teardown(void) {
    uint64_t t0 = plat_now_ns();
    kernel_stop_threads(reboot_idle);
    backend_clear_window();
    backend_reset();
    const ResetFn *start = __start_resets, *stop = __stop_resets;
    __asm__("" : "+r"(start), "+r"(stop));  // separate objects: keep the compiler from reasoning about them
    int n = 0;
    for (const ResetFn *p = start; p < stop; p++)
        if (*p) { (*p)(); n++; }
    kernel_reset();
    if (!plat_reset_guest(GUEST_LO, GUEST_HI)) FATAL("cannot reset guest memory\n");
    backend_guest_memory_reset();
    g_nmodules = 0;
    g_reboot = RT_REBOOT_NONE;
    LOG("[reboot] game torn down in %llums (%d reset hooks)\n", (unsigned long long)((plat_now_ns() - t0) / 1000000), n);
}

// Scarlet 4.0.0: adapted from the v4.0.0 60FPS community frame-duration
// constant (MAIN+0x03c2fbb0: 33333334ns -> 16666667ns). The other community
// write targets an uncommitted guest region in this AOT runtime, so we DO NOT
// blindly write there; NVN interval is changed through our host window hook.
// Guard by actual module memory size and the original 30Hz value.
bool g_scarlet_native_fps60;
static void scarlet_fps60_setup(void) {
    g_scarlet_native_fps60 = false;
#ifdef SCARLET_AOT
    const char *e = getenv("SCARLET_FPS60");
    if (!e || strcmp(e, "1") != 0) return;
    if (g_program_id != 0x0100a3d008c5c000ull || !g_nmodules ||
        g_modules[0].base != MAIN_BASE ||
        g_modules[0].size < 0x03c2fbb0ull + sizeof(uint32_t)) {
        LOG("[scarlet-fps60] unsafe module/program for 60Hz patch; left at 30\n");
        return;
    }
    uint32_t *ns = (uint32_t *)(uintptr_t)(MAIN_BASE + 0x03c2fbb0ull);
    const uint32_t before = *ns;
    if (before != 0x01fca056u && before != 0x00fe502bu) {
        LOG("[scarlet-fps60] frame duration unexpected: 0x%08x (expected 0x01fca056); 60Hz disabled\n", before);
        return;
    }
    *ns = 0x00fe502bu;
    g_scarlet_native_fps60 = true;
    LOG("[scarlet-fps60] 4.0.0 native experimental: 33333334 -> 16666667 ns; Vulkan interval 1. Validate world/animations/battle speed.\n");
#endif
}

static void boot(const char *root) {
    scarlet_main_init_early = false;  // also reset on in-place reboots
    char exefs[1024], romfs[1024], npdm_path[1024];
    snprintf(exefs, sizeof exefs, "%s/exefs", root);
    snprintf(romfs, sizeof romfs, "%s/romfs", root);
    snprintf(npdm_path, sizeof npdm_path, "%s/main.npdm", exefs);
    if (!g_romfs_dir) g_romfs_dir = strdup(romfs);

#ifdef __linux__
    {   // the window and graphics device first (normally made by the start screen or ui_run), so the guest heap can be
        // the driver's memory before any game thread runs (runtime/nvn/vulkan/exec.c backend_guest_heap_prepare)
        extern void ui_window_init(void);
        extern void backend_guest_heap_prepare(void);
        ui_window_init();
        backend_guest_heap_prepare();
    }
#endif
    char why[512];
    if (!game_version_select(root, why, sizeof why)) FATAL("%s\n", why);  // (the address table: game_addresses.h)
    if (!gamelib_load(root, why, sizeof why)) FATAL("%s\n", why);
    loader_load(exefs);
    rando_boot();  // the chosen seed's data patches go into the freshly loaded module
    { extern void settings_load(void); settings_load(); }
    kernel_init();
    dispatch_init();

    uint32_t stack_size = 0x100000;
    int prio = 44;
    FILE *f = fopen(npdm_path, "rb");
    if (f) {
        uint8_t meta[0x80];
        if (fread(meta, 1, sizeof meta, f) == sizeof meta && !memcmp(meta, "META", 4)) {
            prio = meta[0xE];
            stack_size = *(uint32_t *)(meta + 0x1C);
            g_system_resource_size = *(uint32_t *)(meta + 0x14);
            uint8_t aci0[0x18];  // the program ID: ACI0 (offset at META+0x70) +0x10
            if (!fseek(f, *(uint32_t *)(meta + 0x70), SEEK_SET) && fread(aci0, 1, sizeof aci0, f) == sizeof aci0 &&
                !memcmp(aci0, "ACI0", 4))
                g_program_id = *(uint64_t *)(aci0 + 0x10);
        }
        fclose(f);
    }
    g_game_is_la = g_program_id == 0x01006BB00C6F0000ull;
    if (!g_game_is_la) LOG("not Link's Awakening: its game hooks are off\n");
    LOG("main thread: prio %d, stack 0x%x, program 0x%016llx\n", prio, stack_size, (unsigned long long)g_program_id);
    scarlet_fps60_setup();

    // nn::init::Start(thread_handle, args_region, init_sdk, init_main); newer SDKs (19: Pokémon Legends Z-A) add a
    // third callback, run after nnMain returns (the modules' finalizers: nothing to do here)
    uint64_t start = loader_find_symbol("_ZN2nn4init5StartEmmPFvvES2_");
    if (!start) start = loader_find_symbol("_ZN2nn4init5StartEmmPFvvES2_S2_");
    if (!start) FATAL("nn::init::Start not found\n");
    uint64_t init_fn = hle_register("<rtld_init_sdk>", rtld_init_sdk);
    uint64_t fini_fn = hle_register("<rtld_init_main>", rtld_init_main);
    uint64_t exit_fn = hle_register("<rtld_fini>", rtld_fini);
    KThread *t = kernel_create_main_thread(start, stack_size, prio);
    kernel_run_main(t, t->handle, 0, init_fn, fini_fn, exit_fn);
}

// The log's first line after the log's own: this build and the machine, for bug reports. Nothing that identifies the
// player (platform.h plat_system_info). Once per session: a restart of this process (the start screen re-executing
// itself for the game) appends to the same log and inherits LASRECOMP_INFO_LOGGED.
static void log_startup_info(void) {
    if (getenv("LASRECOMP_INFO_LOGGED")) return;
    setenv("LASRECOMP_INFO_LOGGED", "1", 1);
    extern const char *larecomp_version(void);  // runtime/ui/launcher.mm
    PlatSysInfo si = {0};
    plat_system_info(&si);
    char cores[96] = "";
    if (si.cores > 0) {
        int n = snprintf(cores, sizeof cores, " %d cores", si.cores);
        if (si.cores_detail[0]) n += snprintf(cores + n, sizeof cores - n, " (%s)", si.cores_detail);
        if (si.threads > si.cores) snprintf(cores + n, sizeof cores - n, " / %d threads", si.threads);
    } else if (si.threads > 0) snprintf(cores, sizeof cores, " %d threads", si.threads);
    unsigned long long tenths = (si.ram * 10 + (1ull << 29)) >> 30;  // (GB to a tenth; whole when it is: 64 GB, 14.5 GB)
    char ram[32] = "RAM unknown";
    if (si.ram && tenths % 10) snprintf(ram, sizeof ram, "%llu.%llu GB RAM", tenths / 10, tenths % 10);
    else if (si.ram) snprintf(ram, sizeof ram, "%llu GB RAM", tenths / 10);
    fprintf(stderr, "[info] ZA Recomp %s, %s, %s%s, %s%s%s\n", larecomp_version(), si.os[0] ? si.os : "unknown OS",
            si.cpu[0] ? si.cpu : "unknown CPU", cores, ram, si.package ? ", " : "", si.package ? si.package : "");
}

int main(int argc, char **argv) {
#if defined(SCARLET_AOT) && defined(_WIN32)
    // The Win32 launcher has the original Scarlet PC GDI+ layout and
    // is separate from the game. "--play" always skips this step.
    if (argc == 1 && !getenv("LARECOMP_INPUT") &&
        !getenv("LARECOMP_HOST_INPUT") && !getenv("LARECOMP_REEXEC"))
        return scarlet_launch_original_ui();
#endif
    plat_init();
    log_startup_info();
    if (getenv("LARECOMP_REEXEC")) {  // (reserve_guest_space started this process again)
        const char *why = getenv("LARECOMP_REEXEC_WHY"), *n = getenv("LARECOMP_REEXEC");
        if (!why) LOG("[boot] started again (try %s) (LARECOMP_REEXEC set by the caller)\n", n);
        else if (!strcmp(why, REEXEC_FORCED)) LOG("[boot] started again (try %s): %s\n", n, why);
        else LOG("[boot] started again (try %s): the guest address range was in use%s%s\n", n, *why ? ": " : "", why);
    }
#ifdef _WIN32
    setvbuf(stderr, NULL, _IONBF, 0);  // the Windows CRT treats _IOLBF as full buffering
#else
    setvbuf(stderr, NULL, _IOLBF, 0);
#endif
    const char *root = "extracted";  // (in the data root)
    // LARECOMP_NO_LAUNCHER=1 (tools/game_slot.sh sets it for every test run): never the start screen - it can
    // delete game files, and a test's extracted/ may be a link to someone else's. Where it would come up (a forced
    // start screen, "Title screen" in game) the app exits instead. =0: off (start screen tests, scratch data root).
    const char *nl = getenv("LARECOMP_NO_LAUNCHER");
    bool no_launcher = nl && *nl && strcmp(nl, "0");
    bool skip_launcher = no_launcher || getenv("LARECOMP_INPUT");  // tests boot straight in
    if (getenv("LARECOMP_FORCE_LAUNCHER")) skip_launcher = false;  // (test: the start screen, then the scripted input)
#ifdef SCARLET_AOT
    // The default Scarlet user workflow is ALWAYS the launcher when opened
    // without arguments. Stale test environment variables must not silently
    // boot a missing/extracted Z-A root or show a black screen. Explicit
    // --play and scripted runs are still supported below.
    if (argc == 1 && !getenv("LARECOMP_INPUT") && !getenv("LARECOMP_HOST_INPUT")) {
        if (no_launcher || skip_launcher)
            LOG("[scarlet] ignoring inherited LARECOMP_NO_LAUNCHER for normal start; use --play for direct testing\n");
        no_launcher = false;
        skip_launcher = false;
    }
#endif
    static char arg_root[1024];
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--play")) skip_launcher = true;
        else if (argv[i][0] != '-' && !realpath(argv[i], arg_root)) root = argv[i];  // (relative to where we started)
        else if (argv[i][0] != '-') root = arg_root;
    }
#if defined(SCARLET_AOT) && defined(_WIN32)
    // The Scarlet executable is portable: put extracted NSP/XCI images, DLCs,
    // saves and caches beside scarlet.exe (normally on D:), not on a possibly
    // full C: / AppData folder. User/test-specified LARECOMP_DATA_ROOT wins.
    if (!getenv("LARECOMP_DATA_ROOT")) {
        const char *exe_home = SDL_GetBasePath();
        if (exe_home && *exe_home) setenv("LARECOMP_DATA_ROOT", exe_home, 0);
    }
#endif
    rt_paths_init();  // the data root becomes the working directory (runtime/paths.h)
    {   // Pokémon Legends Z-A (exefs/main build 7222e13ecf6adb32: 1.0.0, 8a1c86c437394b69: 2.0.0,
        // b1f12fd919eae86a: 2.0.2): the start screen sets its files up from the player's packages (zaimport). Started
        // without a log redirect (a double click): the log goes to logs/play.log (the previous one: logs/play-anterior.log).
        static const uint8_t za_build[][8] = {{0x72, 0x22, 0xe1, 0x3e, 0xcf, 0x6a, 0xdb, 0x32},
                                              {0x8a, 0x1c, 0x86, 0xc4, 0x37, 0x39, 0x4b, 0x69},
                                              {0xb1, 0xf1, 0x2f, 0xd9, 0x19, 0xea, 0xe8, 0x6a}};
        char mp[1100];
        uint8_t id[8] = {0};
        snprintf(mp, sizeof mp, "%s/exefs/main", root);
        FILE *f = fopen(mp, "rb");
        if (f) { fseek(f, 0x40, SEEK_SET); if (fread(id, 1, 8, f) != 8) memset(id, 0, 8); fclose(f); }
        if (!memcmp(id, za_build[0], 8) || !memcmp(id, za_build[1], 8) || !memcmp(id, za_build[2], 8)) {
            // (the start screen is ZA Recomp's own since v0.1.9: shown on every start, set up or not - Play,
            // Mods, Saves; --play still goes straight into the game)
#ifdef _WIN32
            extern int rt_stderr_is_console(void);
            if (rt_stderr_is_console()) {
                SDL_CreateDirectory("logs");
                remove("logs/play-anterior.log");
                rename("logs/play.log", "logs/play-anterior.log");
                if (freopen("logs/play.log", "w", stderr)) {
                    setvbuf(stderr, NULL, _IONBF, 0);
                    extern void rt_log_moved(const char *path);
                    rt_log_moved("logs/play.log");  // (the crash dialog's "Log file:")
                }
            }
#endif
            // the button icons, if this copy never got them (set up before they existed): made aside for the next
            // start (runtime/ui/launcher.mm; not in scripted runs, which compare pictures)
            extern void launcher_prompts_kick(const char *root);
            if (skip_launcher && !getenv("LARECOMP_INPUT") && !getenv("LARECOMP_HOST_INPUT"))
                launcher_prompts_kick(root);
        }
    }
    log_system();
    for (bool title = !skip_launcher;;) {
        if (title && no_launcher) {
            fprintf(stderr, "[main] LARECOMP_NO_LAUNCHER is set: not showing the start screen - exiting\n");
            exit(3);
        }
        if (title) {  // start screen (runtime/ui/launcher.mm): game files setup, seed choice, settings
#ifdef SCARLET_AOT
            LOG("[scarlet] entering native Scarlet launcher before game boot\n");
#endif
            extern void launcher_run(const char *root);
            launcher_run(root);
#ifdef SCARLET_AOT
            // The standalone Scarlet launcher imports to an isolated selected
            // game root. --play test runs still honour their explicit root.
            extern const char *scarlet_launcher_game_root(void);
            root = scarlet_launcher_game_root();
#endif
        }
        boot(root);
        int kind = ui_run();  // window and input on the main thread; returns when a reboot is requested
        teardown();
        title = kind == RT_REBOOT_TITLE;
    }
}
