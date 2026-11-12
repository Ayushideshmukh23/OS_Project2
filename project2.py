"""Three-customer transaction milestone for the bank simulation."""

from __future__ import annotations

import random
import sys
import threading
import time
from typing import Callable, Sequence, TextIO


NUM_TELLERS = 3
NUM_CUSTOMERS = 3


class BankSimulation:
    """Coordinate tellers and customers using shared memory and semaphores."""

    def __init__(
        self,
        output: TextIO = sys.stdout,
        transaction_choices: Sequence[str] | None = None,
        sleep_function: Callable[[float], None] = time.sleep,
    ) -> None:
        if transaction_choices is not None:
            if len(transaction_choices) != NUM_CUSTOMERS:
                raise ValueError(f"Provide exactly {NUM_CUSTOMERS} transactions")
            if any(
                transaction not in {"Deposit", "Withdrawal"}
                for transaction in transaction_choices
            ):
                raise ValueError("Transactions must be Deposit or Withdrawal")

        self.output = output
        self.transaction_choices = transaction_choices
        self.sleep_function = sleep_function

        # These semaphores coordinate bank-wide resources and conditions.
        self.print_semaphore = threading.Semaphore(1)
        self.state_semaphore = threading.Semaphore(1)
        self.bank_open = threading.Semaphore(0)
        self.door = threading.Semaphore(2)
        self.available_teller_count = threading.Semaphore(0)
        self.manager = threading.Semaphore(1)
        self.safe = threading.Semaphore(2)

        # Shared memory protected by state_semaphore.
        self.ready_teller_count = 0
        self.available_tellers: list[int] = []
        self.assigned_customers: list[int | None] = [None] * NUM_TELLERS
        self.teller_transactions: list[str | None] = [None] * NUM_TELLERS

        # Each teller has a private handshake with its assigned customer.
        self.customer_arrived = [threading.Semaphore(0) for _ in range(NUM_TELLERS)]
        self.customer_acknowledged = [
            threading.Semaphore(0) for _ in range(NUM_TELLERS)
        ]
        self.transaction_requested = [
            threading.Semaphore(0) for _ in range(NUM_TELLERS)
        ]
        self.transaction_supplied = [
            threading.Semaphore(0) for _ in range(NUM_TELLERS)
        ]
        self.transaction_completed = [
            threading.Semaphore(0) for _ in range(NUM_TELLERS)
        ]
        self.customer_left = [threading.Semaphore(0) for _ in range(NUM_TELLERS)]
        self.threads: list[threading.Thread] = []

    def print_action(self, message: str) -> None:
        """Print one complete line without another thread interrupting it."""
        with self.print_semaphore:
            print(message, file=self.output, flush=True)

    def teller(self, teller_id: int) -> None:
        """Serve one customer through introduction and transaction completion."""
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

        self.print_action(
            f"Teller {teller_id} [Customer {customer_id}]: asks for transaction"
        )
        self.transaction_requested[teller_id].release()
        self.transaction_supplied[teller_id].acquire()

        with self.state_semaphore:
            transaction = self.teller_transactions[teller_id]

        if transaction is None:
            raise RuntimeError(f"Teller {teller_id} received no transaction")

        if transaction == "Withdrawal":
            self.use_manager(teller_id, customer_id)

        self.use_safe(teller_id, customer_id)
        self.print_action(
            f"Teller {teller_id} [Customer {customer_id}]: "
            "informs customer transaction is complete"
        )
        self.transaction_completed[teller_id].release()

        self.customer_left[teller_id].acquire()
        self.print_action(
            f"Teller {teller_id} [Customer {customer_id}]: finishes serving customer"
        )

    def use_manager(self, teller_id: int, customer_id: int) -> None:
        """Obtain exclusive manager permission for a withdrawal."""
        self.print_action(
            f"Teller {teller_id} [Customer {customer_id}]: is going to manager"
        )
        with self.manager:
            delay_ms = random.randint(5, 30)
            self.print_action(
                f"Teller {teller_id} [Customer {customer_id}]: "
                f"is using manager for {delay_ms} milliseconds"
            )
            self.sleep_function(delay_ms / 1000)
            self.print_action(
                f"Teller {teller_id} [Customer {customer_id}]: is leaving manager"
            )

    def use_safe(self, teller_id: int, customer_id: int) -> None:
        """Use one of the two available spaces in the safe."""
        self.print_action(
            f"Teller {teller_id} [Customer {customer_id}]: is going to safe"
        )
        with self.safe:
            delay_ms = random.randint(10, 50)
            self.print_action(
                f"Teller {teller_id} [Customer {customer_id}]: "
                f"is using safe for {delay_ms} milliseconds"
            )
            self.sleep_function(delay_ms / 1000)
            self.print_action(
                f"Teller {teller_id} [Customer {customer_id}]: is leaving safe"
            )

    def customer(self, customer_id: int) -> None:
        """Choose a transaction and complete it with one assigned teller."""
        if self.transaction_choices is None:
            transaction = random.choice(["Deposit", "Withdrawal"])
        else:
            transaction = self.transaction_choices[customer_id]

        self.print_action(f"Customer {customer_id}: selects {transaction} transaction")
        delay_ms = random.randint(0, 100)
        self.print_action(
            f"Customer {customer_id}: begins random wait for {delay_ms} milliseconds"
        )
        self.sleep_function(delay_ms / 1000)
        self.print_action(f"Customer {customer_id}: finishes random wait")

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
        self.transaction_requested[teller_id].acquire()
        with self.state_semaphore:
            self.teller_transactions[teller_id] = transaction

        self.print_action(
            f"Customer {customer_id} [Teller {teller_id}]: "
            f"gives {transaction} transaction"
        )
        self.transaction_supplied[teller_id].release()

        self.transaction_completed[teller_id].acquire()
        with self.door:
            self.print_action(
                f"Customer {customer_id} [Teller {teller_id}]: leaves the bank"
            )

        self.customer_left[teller_id].release()

    def run(self) -> None:
        """Start and join every teller and customer thread."""
        teller_threads = [
            threading.Thread(
                target=self.teller, args=(teller_id,), name=f"Teller-{teller_id}"
            )
            for teller_id in range(NUM_TELLERS)
        ]
        customer_threads = [
            threading.Thread(
                target=self.customer,
                args=(customer_id,),
                name=f"Customer-{customer_id}",
            )
            for customer_id in range(NUM_CUSTOMERS)
        ]
        self.threads = teller_threads + customer_threads

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
