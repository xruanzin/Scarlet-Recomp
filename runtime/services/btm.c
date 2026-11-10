// Horizon btm:u (Bluetooth Manager user interface).
// On firmware 5.0.0+, cmd 0 GetCore returns IBtmUserCore as an IPC object.
// Returning ResultSuccess with no object (the generic logger's old behavior)
// causes the guest to parse a nonexistent move handle and may abort.
// This provides a valid interface and events, but does not emulate BLE radio.
#include <stdint.h>
#include "../hle.h"
#include "../ipc.h"

static uint32_t bt_event_handle(void) {
    uint32_t write_handle = 0, read_handle = 0;
    kernel_create_event_pair(&write_handle, &read_handle);
    return read_handle;
}

static void btm_user_core(Service *s, IpcReq *req, IpcResp *resp) {
    (void)s;
    switch (req->cmd) {
    // The event acquisitions return (bool success, readable event handle).
    // Events remain unsignalled: no actual BLE scan/connection exists.
    case 0:   // AcquireBleScanEvent
    case 17:  // AcquireBleConnectionEvent
    case 21:  // AcquireBlePairingEvent
    case 26:  // AcquireBleServiceDiscoveryEvent
    case 33:  // AcquireBleMtuConfigEvent
        resp->copy_handles[resp->ncopy++] = bt_event_handle();
        OUT(uint8_t, 0) = 1;
        resp_size(resp, 1);
        LOG("[btm:u] IBtmUserCore event cmd %u -> unsignalled event\n", req->cmd);
        return;

    // On the host runtime no Switch BLE devices are connected.
    // Return a zero count; never claim to have discovered a device.
    case 5:   // GetBleScanResultsForGeneral
    case 10:  // GetBleScanResultsForSmartDevice
    case 20:  // BleGetConnectionState
    case 25:  // BleGetPairedDevices
    case 27:  // GetGattServices
    case 29:  // GetGattIncludedServices
    case 31:  // GetGattCharacteristics
    case 32:  // GetGattDescriptors
        OUT(uint8_t, 0) = 0;
        resp_size(resp, 1);
        return;

    default:
        LOG("[btm:u] IBtmUserCore unsupported cmd %u\n", req->cmd);
        resp->result = MAKE_RESULT(1, 1);
        return;
    }
}

SERVICE("btm:u", btm_u) {
    (void)s;
    if (req->cmd == 0) {
        LOG("[btm:u] GetCore -> IBtmUserCore\n");
        ipc_return_object(resp, service_new("IBtmUserCore", btm_user_core, NULL));
    } else {
        LOG("[btm:u] unsupported root cmd %u\n", req->cmd);
        resp->result = MAKE_RESULT(1, 1);
    }
}
