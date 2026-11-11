# Development Log

## November 10, 2026 — Beginning (6:27:12 PM CST)

This is my first work session for Operating Systems Project 2. The project is a bank simulation using Python threads, semaphores, and shared memory. The final version needs 3 teller threads and 50 customer threads, but I am starting with 3 customers so the synchronization is easier to understand and test.

Today I want to make the tellers become ready, open the bank only after all 3 tellers are ready, pair each customer with an available teller, and complete a simple introduction between each customer and teller. I want to keep this first version small and make sure I understand how the shared teller list and semaphores coordinate the threads before adding more steps. The manager, safe, and full transactions will be added later.
