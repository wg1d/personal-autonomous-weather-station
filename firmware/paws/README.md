# PAWS firmware

Firmware of the Personal Autonomous Weather Station: an ESP32 that wakes
up every 15 minutes, measures temperature, humidity and pressure, stores
the row on an SD card, uploads the new rows once per hour, and goes back
to deep sleep.

The design and the step-by-step construction of this firmware are
explained in the [PAWS book](https://wg1d.github.io/personal-autonomous-weather-station/),
Phase 4 (Architecture). This documentation describes the code itself.

## Structure

The code is split into three layers, which only communicate through
interfaces (*ports and adapters*):

| Layer | Folder | Content |
|-------|--------|---------|
| Interfaces | `lib/ports/` | What the core needs from the outside world: IClock, ISensor, IStorage, INetwork, IPower, IMaintenance, ILog, and the data they exchange (Record, Measurement). |
| Core | `lib/core/` | The decision logic, without any hardware access: Config, the rules (Rules.h), the transitions (nextState()) and the StateMachine. |
| Adapters | `src/adapters/` | The implementations of the interfaces for the board. |

The tests (`test/`) replace the adapters with test doubles, such as
FakeClock or MockNetwork, and run the core on the computer.

## Where to start

1. StateMachine::run(): one wake-up, from `BOOT` to `SLEEP`.
2. nextState(): all the transitions of the state machine, in one pure
   function.
3. The interfaces, starting with IClock.

## Commands

From the root of the repository:

```bash
pixi run test             # unit and scenario tests on the computer
pixi run build-firmware   # build the firmware for the board
pixi run api-docs         # this documentation (after pixi run book)
```
