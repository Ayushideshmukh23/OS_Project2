# Development Log

## November 10, 2026 — Beginning (6:27:12 PM CST)

This is my first work session for Operating Systems Project 2. The project is a bank simulation using Python threads, semaphores, and shared memory. The final version needs 3 teller threads and 50 customer threads, but I am starting with 3 customers so the synchronization is easier to understand and test.

Today I want to make the tellers become ready, open the bank only after all 3 tellers are ready, pair each customer with an available teller, and complete a simple introduction between each customer and teller. I want to keep this first version small and make sure I understand how the shared teller list and semaphores coordinate the threads before adding more steps. The manager, safe, and full transactions will be added later.

## November 10, 2026 — Ending (6:36:31 PM CST)

I completed the first synchronization milestone with 3 teller threads and 3 customer threads. All three tellers announce that they are ready before the last teller opens the bank. Each customer enters through the two-person door semaphore, takes one teller from the shared available-teller list, introduces itself, waits for an acknowledgment, and then leaves. The teller waits for that customer to leave before its thread finishes. The shared ready count, teller list, and assignments are protected by a state semaphore. Counting semaphores represent the open bank and available tellers, and each teller has separate semaphores for the introduction, acknowledgment, and departure steps. A print semaphore keeps each output line together.

I ran the 3-test unit test suite once with detailed output and then 10 more times, for 33 passing tests total. I also ran the program directly once and it ended without hanging or showing a traceback. The tests checked that all teller-ready messages come before the bank opens and customers enter, that each customer gets exactly one teller and acknowledgment, and that acknowledgment happens before the customer leaves and the teller finishes. The first bytecode compilation attempt hit a macOS cache permission error outside the project folder, so I redirected the Python cache to `/tmp` and the compilation passed. During review I also noticed a possible ordering race in the readiness messages and moved that output into the semaphore-protected readiness section before running the tests.

Next time I still need to expand to 50 customers and let tellers serve repeatedly, add random transaction choices and delays, and implement the full customer/teller transaction handshake. The manager and safe semaphores, withdrawal behavior, final shutdown, and full-specification testing also remain unfinished.
