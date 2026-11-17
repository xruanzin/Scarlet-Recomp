# Scarlet native FPS investigation

Status: unfinished; gameplay speed has not been validated.

## Continuation evidence, 2026-11-15

The diagnostic launcher now owns its entire process tree with a Windows Job
Object, retains real log file handles across the reservation re-exec, and
waits for each observed process object as well as zero active Job processes.
Job accounting can reach zero before inherited handles are released. A real
game teardown exceeded the original 10-second allowance; it is now 60 seconds.
`test_owned_process.py` exercises logs after parent exit and whole-tree stop.
Only owned diagnostic processes are terminated; no existing game is attached.
The launcher records launch cwd and the runtime's private userdata cwd.

Sequential re-exec tests `20261115-062755-258-30` and
`20261115-062856-527-60` each recorded two processes and zero active processes
at completion. `build/native-timing-comparison.json` separates cold startup
from intervals near the requested presentation rate. The latter supplied
9.112194749 seconds over 9.0739966 wall seconds at 30 FPS, and 37.779640111
over 37.3045078 at 60 FPS. These are clock supplies, not completed simulation.
Filtering near-target intervals is selection, not a proof of speed over the
entire run; stalls and loading remain visible in the complete report.

New AOT observation at `main+0xd07ad8` preserves the original LDP and logs
the float selected by the original FCSEL. All ten instructions in the
selector are checked against Scarlet's NSO. The live selector has flag=1,
mode=0 and retains variable seconds (approximately 0.0169 at 60 FPS).
The next direct call passes s8 via s0 at d07c80/d07c84 to d09394, which
references the profiler string `hkaiWorld::stepWorld` at 3b374ef. This
identifies a Havok AI path, not a universal physics or animation clock.
Evidence: `native-clock1-downstream.txt`, `native-clock1-effective-loop.txt`,
`native-clock1-world-step.txt` and the effective-consumer run logs.
Thread IDs are included because worker scheduling migrates this consumer;
its per-thread totals must not be treated as one global completed-step count.
Getter samples are keyed by caller AND index so the history reader cannot
exhaust the sample limit before all seven indices are represented.

Generation completed 1379 main chunks in 209 seconds. Incremental build
`build/native-effective-build.log` linked the EXE and DLL; verification
`build/native-effective-verify.log` returned MAKE_EXIT=0. The runtime-only
log adjustment also returned MAKE_EXIT=0 in `native-effective-thread-build.log`.
Current DLL ID: `7b7701a8a7ef5d4f-421C5411B487EB4D`, accepted by the runtime
in the subsequent live runs. Backup before regeneration:
`build/native-fps-backup-consumer-20261115-063344`.
NSO guard tests now reject mutations to all 37 validated instructions.

Actual internal Vulkan captures in run `20261115-144324-516-60` show the
title at frame 300 and loaded exterior gameplay at frame 3000. Subsequent
private-save movement runs `20261115-144558-179-30` and
`20261115-144829-423-60` held the stick for 100 and 200 presented frames,
respectively. Their final screenshots show similar exterior positions;
this is qualitative evidence only, not coordinate-based speed validation.
The 60 FPS run hit the old teardown timeout after its gameplay capture;
finally cleanup finished and a process query found no Scarlet remaining.
The timeout adjustment requires a fresh real-game teardown check.

Six actual Scarlet Lua archive members were decoded OFFLINE using the
existing standalone analysis helper in `third_party/ooz`, never linked into
the game runtime. All declared decoded sizes and full Lua chunk parses agree.
`build/scarlet-script-analysis/decoded-manifest.json` records hashes and sizes.
Only main.blua has the thirteen 1/30 double constants. Its SHA-256 is
`c1a4f4e2625912cf0b739a642a79ba3357df0557a544b92da22a6cb139de2815`.
Two constants belong to fixed-step accumulators (prototypes 0.17518 and
0.17747), but other uses include divisors and defaults. In particular,
0.17748 integrates position with its dt argument even when count is zero;
the count flows to several other subsystems. Replacing the accumulator
constant is therefore NOT yet a demonstrated fix for indoor jitter.
No script constants have been changed. Remaining work is to trace those
count consumers and correlate their execution with an interior scene.

## Live consumer evidence, 2026-11-14

`build/native-consumers-live.txt` disassembles getter callers observed in the
30 FPS trace. `0xb45728` checks for zero to gate task execution. `0xd07a4c`
loads clock 1's signed integer nanoseconds, converts to double, divides by
1e9 and forwards float seconds to `0xd07a7c`. `0xc3a2c0` similarly converts
clock 1 and subtracts seconds from a state value. These are distinct from
the history collector at `0x2b7aa24`.

The runtime now supplies measured time only at the observed clock-1 producer
(`92dd2c`, caller `7002b7a934`, vtable `7004440158`, receiver `700092dd38`).
Zero gates and all other indices are preserved by this hook. The old static
frame-period experiment in main.c still affects the shared period table and
needs further review; the full replacement is not complete.

The generator additionally validates all six original instructions of the
seconds consumer. Guard tests reject mutations to 27 instructions, identity,
table and relocation. `test_native_clock.c` executes the actual runtime code
with deterministic monotonic time; startup, 30/60 caps, sustained 40ms frames,
loading-stall reset and domain gates passed.

Build `native-clock1-build.log` completed with MAKE_EXIT=0 and DLL ID
`a7036bd46721d800-421C5411B487EB4D`. Live run
`build/native-timing-runs/20261114-134752-799-60` loaded that DLL. The reader
summary `build/native-clock1-readers.json` records actual clock-1 reads at
16.67ms and variable values through 79.17ms. This proves delivery to readers,
not correct displacement, animation duration, battle timing or indoor scripts.
`clock1_supplied_ns` counts supplied time, not completed gameplay advancement.
Getter tracing is now bounded per distinct caller/thread to avoid poll-loop
log floods. No Windows automation tools were used for these runs.

The active target is the original Scarlet 4.0.0 main build
`421c5411b487eb4d049dd065fec9547773e8e598`. No game files are modified.

## Evidence recovered from Scarlet

`tools/scarlet/inspect_native_timing.py` scans the whole text section for
vtable slot-2 tail dispatch. Nine matches are in
`build/native-timing-callers.json`, including original instructions,
direct branch search results, relocations and NSO SHA-256.
There are no direct branches into the searched 32-byte prefixes; this does
not exclude indirect callers. Most candidates have relocation references.

Three matches load x2 from a period table before dispatching: main+0x92dd2c,
main+0x2b7b314, main+0x2b7b340. Their ADRP/LDR resolves to slot 0x46d8bc0;
the original RELATIVE relocation resolves that slot to 0x3c2fba8. The table
contains 16666667, 33333334, 50000000, 66666667 and 83333334 nanoseconds.
The existing static 60 FPS modification writes the second table element.
This is stronger evidence of a timing argument, but does not establish
which callback advances simulation or whether it runs once per frame.

`tools/scarlet/native_timing.py` validates the exact build, table relocation,
all five table values and all six instructions of each thunk. It adds
validated AOT calls, retaining the original load into x8. Runtime
logging is enabled by SCARLET_TIMING_TRACE. The log records caller, object,
x1 and supplied x2; it does not label the sum as simulation advancement.

## Reference limitations

KarPur runtime/frame_dt.c measures eight intervals and replaces a nanosecond
argument. Its runtime/frame_rate.c includes TotK-specific logic that should
not be transplanted. KarPur runtime/data_patch.c replaces every matching
double 1/30 in decoded buffers; that does not satisfy the selective-script
validation required here. Its archived progress reports Lua TValue readers
and 13 decoded occurrences but does not identify their script functions.

Sources: https://github.com/Grunttanamo/KarPur/blob/main/runtime/frame_dt.c,
https://github.com/Grunttanamo/KarPur/blob/main/runtime/data_patch.c,
https://github.com/Grunttanamo/KarPur/blob/main/docs/progress-archive-de.md.

## Next required checks

1. Measure actual displacement and completed animation/physics work at 30/60,
   separately from supplied clock time and queue-accepted presentations.
2. Trace the Lua fixed-step count consumers in an interior scene before any
   selective native script adjustment. No blanket double replacement.
3. Review other clock domains and the shared static period table experiment.
4. Validate indoor, battle, F1/F11 and resolution behavior. Exterior rendering
   and approximate displacement do not establish these remaining requirements.

REA's Ghidra provider currently reports an unavailable JDK path (21.0.11).
Existing Capstone 5.0.7 and the repository NSO loader support the static
instruction/relocation work above; no REA configuration was changed.
