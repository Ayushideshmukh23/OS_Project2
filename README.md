# Operating Systems Project 2 — Bank Simulation

This program simulates a bank using Python threads, shared memory, and semaphores. It starts exactly 3 teller threads and 50 customer threads. Customers choose a deposit or withdrawal, wait before entering, use an available teller, complete the transaction handshake, and leave. Tellers repeatedly serve customers until the bank shuts down cleanly.

## Requirements and commands

The project uses only the Python standard library. It was developed and tested locally with Python 3.9.6.

Run the simulation:

```sh
python3 project2.py
```

Run the automated tests:

```sh
python3 -m unittest -v
```

## Synchronization

- `bank_open` blocks all customers until all 3 tellers are ready.
- `door` is `Semaphore(2)`, limiting simultaneous entry and exit passages.
- `available_teller_count` counts tellers ready for another customer.
- `state_semaphore` protects the ready count, available-teller list, customer assignments, and transaction slots in shared memory.
- Per-teller semaphores order customer arrival, acknowledgment, transaction request, transaction supply, completion, and departure.
- `manager` is `Semaphore(1)` and is used only for withdrawals.
- `safe` is `Semaphore(2)` and is used for every transaction.
- `print_semaphore` prevents output from different threads from overlapping.

After all 50 customer threads have left and joined, the main thread sends one shutdown wake-up to each teller, joins all 3 teller threads, and then prints that the bank is closed.
