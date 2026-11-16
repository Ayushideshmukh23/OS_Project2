# Development Log

## November 10, 2026 — Beginning (6:27:12 PM CST)

This is my first work session for Operating Systems Project 2. The project is a bank simulation using Python threads, semaphores, and shared memory. The final version needs 3 teller threads and 50 customer threads, but I am starting with 3 customers so the synchronization is easier to understand and test.

Today I want to make the tellers become ready, open the bank only after all 3 tellers are ready, pair each customer with an available teller, and complete a simple introduction between each customer and teller. I want to keep this first version small and make sure I understand how the shared teller list and semaphores coordinate the threads before adding more steps. The manager, safe, and full transactions will be added later.

## November 10, 2026 — Ending (6:36:31 PM CST)

I completed the first synchronization milestone with 3 teller threads and 3 customer threads. All three tellers announce that they are ready before the last teller opens the bank. Each customer enters through the two-person door semaphore, takes one teller from the shared available-teller list, introduces itself, waits for an acknowledgment, and then leaves. The teller waits for that customer to leave before its thread finishes. The shared ready count, teller list, and assignments are protected by a state semaphore. Counting semaphores represent the open bank and available tellers, and each teller has separate semaphores for the introduction, acknowledgment, and departure steps. A print semaphore keeps each output line together.

I ran the 3-test unit test suite once with detailed output and then 10 more times, for 33 passing tests total. I also ran the program directly once and it ended without hanging or showing a traceback. The tests checked that all teller-ready messages come before the bank opens and customers enter, that each customer gets exactly one teller and acknowledgment, and that acknowledgment happens before the customer leaves and the teller finishes. The first bytecode compilation attempt hit a macOS cache permission error outside the project folder, so I redirected the Python cache to `/tmp` and the compilation passed. During review I also noticed a possible ordering race in the readiness messages and moved that output into the semaphore-protected readiness section before running the tests.

Next time I still need to expand to 50 customers and let tellers serve repeatedly, add random transaction choices and delays, and implement the full customer/teller transaction handshake. The manager and safe semaphores, withdrawal behavior, final shutdown, and full-specification testing also remain unfinished.

## November 11, 2026 — Beginning (8:39:49 PM CST)

Yesterday I completed the basic teller-customer pairing and introduction milestone with 3 tellers and 3 customers. Today I plan to add the transaction communication between each customer and teller, including the teller asking for the transaction, the customer supplying it, and the teller reporting when it is complete. I also want to add the manager semaphore for withdrawals, the safe semaphore for every transaction, and all of the required random delays and messages. I am keeping the simulation at 3 customers today so I can focus on understanding and testing this new synchronization before expanding it to 50 customers.

## November 11, 2026 — Ending (8:44:06 PM CST)

I completed the 3-customer transaction milestone. Customers now randomly choose a deposit or withdrawal during a normal run and wait for a random amount of time before entering. After the introduction, each teller asks for the transaction, the customer supplies it through shared memory, and the teller signals completion before the customer can leave. Per-teller semaphores keep those request, supply, completion, and departure steps in order. Withdrawals acquire a manager semaphore with one permit, so only one teller can interact with the manager at a time. Every transaction acquires a safe semaphore with two permits, so up to two tellers can work in the safe at once. The customer, manager, and safe delays all print messages before and after sleeping.

I added controlled deposit, withdrawal, and mixed-transaction tests. The 7-test suite passed once with detailed output and then passed 10 more complete runs, for 77 passing test executions. I also ran the program directly once after the fix; it randomly used both transaction types in that run, showed two tellers overlapping in the safe without exceeding its limit, and ended normally without hanging or a traceback. The source also compiled successfully with the Python cache directed to `/tmp`. The first test and direct-run attempt failed before the simulation started because Python 3.9 evaluated a newer union type hint at import time. I fixed that by postponing annotation evaluation, then reran all checks successfully.

The next session still needs the final expansion to 50 customers, teller loops that serve multiple customers, a clean way to tell the tellers when the bank is closing, and tests for the full-size run. I also still need to review the final output and submission packaging requirements once the complete version is ready.

## November 15, 2026 — Beginning (6:47:29 PM CST)

The small 3-customer version is working with transaction communication, manager synchronization for withdrawals, and safe synchronization for every transaction. Today my goal is to make each teller repeatedly serve customers, scale the simulation to the required 50 customer threads, and add a clean shutdown that stops all three tellers after every customer has left. I also plan to expand the tests and audit the finished program against every assignment requirement before calling it complete.

## November 15, 2026 — Ending (7:04:42 PM CST)

I completed the final 3-teller and 50-customer version. Each teller now loops back to the shared available-teller list after its customer leaves, so the same teller can serve many customers without overlapping them. After all 50 customer threads join, the main thread stores a shutdown sentinel for each teller and releases each teller's customer-arrival semaphore. That wakes blocked tellers without busy waiting. The main thread joins all three tellers and only then prints that the bank is closed.

I expanded the tests to cover the exact thread counts and IDs, opening order, all 50 customer lifecycles, unique teller assignments, repeated teller service, transaction ordering, deposit and withdrawal manager behavior, manager/safe/door occupancy limits, closing order, thread termination, output format and delay ranges, and final semaphore/shared-memory cleanup. The original 7-test suite passed after repeated service and again after scaling. The first expanded 14-test run had 13 passes and one test-helper error because it tried to parse `0:` as an integer. I fixed the parser, and all 14 tests passed. I then ran the complete 14-test suite 10 consecutive times for 140 more passing test executions, followed by another successful 14-test audit run. Compilation also passed on the local Python 3.9.6 installation.

I ran the real program once with 3 customers while checking shutdown, then ran the real 50-customer program four times. Every full-size run completed with 50 selections, entries, transaction completions, and departures, followed by 3 teller stops and one final bank-closed message. I did not find a runtime synchronization failure. During the line-by-line audit I changed the manager and safe completion messages from "leaving" to the required "done using" wording. I tried noninteractive five-second SSH checks for CS1 and CS2, but CS1's configured hostname and the CS2 hostname could not be resolved, so I could not run or identify the Python version on those systems.

The source code, expanded tests, README, and dev log are ready in the repository. The submission ZIP is intentionally not created yet. The separate professor Git instructions and sample output were never available, so exact compliance with any additional requirements in those documents still cannot be verified.
