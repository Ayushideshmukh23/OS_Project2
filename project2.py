"""First synchronization milestone for the bank simulation.

This version intentionally stops after a customer and teller complete an
introduction. Transactions, the manager, and the safe will be added later.
"""

import sys
import threading
from typing import TextIO


NUM_TELLERS = 3
NUM_CUSTOMERS = 3


class BankSimulation:
    """Coordinate tellers and customers using shared memory and semaphores."""

    def __init__(self, output: TextIO = sys.stdout) -> None:
        self.output = output

        # These semaphores coordinate bank-wide resources and conditions.
        self.print_semaphore = threading.Semaphore(1)
        self.state_semaphore = threading.Semaphore(1)
        self.bank_open = threading.Semaphore(0)
        self.door = threading.Semaphore(2)
        self.available_teller_count = threading.Semaphore(0)

        # Shared memory protected by state_semaphore.
        self.ready_teller_count = 0
        self.available_tellers: list[int] = []
        self.assigned_customers: list[int | None] = [None] * NUM_TELLERS

        # Each teller has a private three-step handshake with its customer.
        self.customer_arrived = [threading.Semaphore(0) for _ in range(NUM_TELLERS)]
        self.customer_acknowledged = [
            threading.Semaphore(0) for _ in range(NUM_TELLERS)
        ]
        self.customer_left = [threading.Semaphore(0) for _ in range(NUM_TELLERS)]

    def print_action(self, message: str) -> None:
        """Print one complete line without another thread interrupting it."""
        with self.print_semaphore:
            print(message, file=self.output, flush=True)

    def teller(self, teller_id: int) -> None:
        """Become available, acknowledge one customer, and wait for departure."""
        with self.state_semaphore:
            self.available_tellers.append(teller_id)
            self.ready_teller_count += 1
            self.available_teller_count.release()
            self.print_action(f"Teller {teller_id}: is ready")

            if self.ready_teller_count == NUM_TELLERS:
                # Printing first makes the bank-opening point unambiguous in output.
                self.print_action(f"Teller {teller_id}: opens the bank")
                for _ in range(NUM_CUSTOMERS):
                    self.bank_open.release()

        self.customer_arrived[teller_id].acquire()
        with self.state_semaphore:
            customer_id = self.assigned_customers[teller_id]

        if customer_id is None:
            raise RuntimeError(f"Teller {teller_id} has no assigned customer")

        self.print_action(
            f"Teller {teller_id} [Customer {customer_id}]: acknowledges customer"
        )
        self.customer_acknowledged[teller_id].release()

        self.customer_left[teller_id].acquire()
        self.print_action(
            f"Teller {teller_id} [Customer {customer_id}]: finishes serving customer"
        )

    def customer(self, customer_id: int) -> None:
        """Enter the open bank, meet one teller, and leave after acknowledgment."""
        self.bank_open.acquire()

        with self.door:
            self.print_action(f"Customer {customer_id}: enters the bank")

        self.available_teller_count.acquire()
        with self.state_semaphore:
            teller_id = self.available_tellers.pop(0)
            self.assigned_customers[teller_id] = customer_id

        self.print_action(
            f"Customer {customer_id} [Teller {teller_id}]: introduces customer"
        )
        self.customer_arrived[teller_id].release()

        self.customer_acknowledged[teller_id].acquire()
        with self.door:
            self.print_action(
                f"Customer {customer_id} [Teller {teller_id}]: leaves the bank"
            )

        self.customer_left[teller_id].release()

    def run(self) -> None:
        """Start and join every teller and customer thread."""
        teller_threads = [
            threading.Thread(target=self.teller, args=(teller_id,))
            for teller_id in range(NUM_TELLERS)
        ]
        customer_threads = [
            threading.Thread(target=self.customer, args=(customer_id,))
            for customer_id in range(NUM_CUSTOMERS)
        ]

        for thread in teller_threads:
            thread.start()
        for thread in customer_threads:
            thread.start()

        for thread in customer_threads:
            thread.join()
        for thread in teller_threads:
            thread.join()


def main() -> None:
    BankSimulation().run()


if __name__ == "__main__":
    main()
