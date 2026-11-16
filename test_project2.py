"""Tests for teller/customer and transaction synchronization."""

from __future__ import annotations

import io
import re
import threading
import unittest
from collections import Counter

from project2 import BankSimulation, NUM_CUSTOMERS, NUM_TELLERS


DEPOSIT = ["Deposit"] * NUM_CUSTOMERS
WITHDRAWAL = ["Withdrawal"] * NUM_CUSTOMERS
MIXED = [
    "Deposit" if customer_id % 2 == 0 else "Withdrawal"
    for customer_id in range(NUM_CUSTOMERS)
]


class BankSimulationTests(unittest.TestCase):
    def run_bank(self, transactions: list[str] | None = None) -> list[str]:
        output = io.StringIO()
        simulation = BankSimulation(
            output=output,
            transaction_choices=transactions or MIXED,
            sleep_function=lambda _seconds: None,
        )
        thread_errors: list[threading.ExceptHookArgs] = []
        original_excepthook = threading.excepthook
        threading.excepthook = lambda args: thread_errors.append(args)
        try:
            simulation.run(timeout=5.0)
        finally:
            threading.excepthook = original_excepthook

        self.assertEqual([], thread_errors, "A worker thread raised an exception")
        self.assertTrue(all(not thread.is_alive() for thread in simulation.threads))
        self.simulation = simulation
        return output.getvalue().splitlines()

    @staticmethod
    def customer_ids_for(lines: list[str], ending: str) -> list[int]:
        return [
            int(line.split()[1].rstrip(":"))
            for line in lines
            if line.startswith("Customer ") and line.endswith(ending)
        ]

    def test_exact_thread_counts_and_unique_ids(self) -> None:
        self.run_bank()
        self.assertEqual(NUM_TELLERS, len(self.simulation.teller_threads))
        self.assertEqual(NUM_CUSTOMERS, len(self.simulation.customer_threads))
        self.assertEqual(
            {f"Teller-{teller_id}" for teller_id in range(NUM_TELLERS)},
            {thread.name for thread in self.simulation.teller_threads},
        )
        self.assertEqual(
            {f"Customer-{customer_id}" for customer_id in range(NUM_CUSTOMERS)},
            {thread.name for thread in self.simulation.customer_threads},
        )

    def test_all_tellers_are_ready_before_any_customer_enters(self) -> None:
        lines = self.run_bank()
        open_index = next(i for i, line in enumerate(lines) if "opens the bank" in line)
        enter_indices = [i for i, line in enumerate(lines) if "enters the bank" in line]
        ready_indices = [i for i, line in enumerate(lines) if "is ready" in line]

        self.assertEqual(NUM_TELLERS, len(ready_indices))
        self.assertEqual(NUM_CUSTOMERS, len(enter_indices))
        self.assertTrue(all(index < open_index for index in ready_indices))
        self.assertTrue(all(index > open_index for index in enter_indices))

    def test_each_customer_has_one_acknowledged_introduction(self) -> None:
        lines = self.run_bank()
        introductions: dict[int, int] = {}
        acknowledgments: set[tuple[int, int]] = set()

        for line in lines:
            introduction = re.fullmatch(
                r"Customer (\d+) \[Teller (\d+)\]: introduces customer", line
            )
            if introduction:
                customer_id, teller_id = map(int, introduction.groups())
                self.assertNotIn(customer_id, introductions)
                introductions[customer_id] = teller_id

            acknowledgment = re.fullmatch(
                r"Teller (\d+) \[Customer (\d+)\]: acknowledges customer", line
            )
            if acknowledgment:
                teller_id, customer_id = map(int, acknowledgment.groups())
                acknowledgments.add((customer_id, teller_id))

        self.assertEqual(set(range(NUM_CUSTOMERS)), set(introductions))
        self.assertEqual(
            {(customer_id, teller_id) for customer_id, teller_id in introductions.items()},
            acknowledgments,
        )
        self.assertEqual(NUM_TELLERS, len(set(introductions.values())))

    def test_all_customers_enter_complete_and_leave_once(self) -> None:
        lines = self.run_bank()
        expected_ids = list(range(NUM_CUSTOMERS))
        entered = sorted(self.customer_ids_for(lines, "enters the bank"))
        left = sorted(self.customer_ids_for(lines, "leaves the bank"))
        completed = sorted(
            int(match.group(1))
            for line in lines
            if (
                match := re.fullmatch(
                    r"Teller \d+ \[Customer (\d+)\]: "
                    r"informs customer transaction is complete",
                    line,
                )
            )
        )

        self.assertEqual(expected_ids, entered)
        self.assertEqual(expected_ids, completed)
        self.assertEqual(expected_ids, left)

    def test_transaction_handshake_and_departure_order(self) -> None:
        lines = self.run_bank(MIXED)

        for customer_id, transaction in enumerate(MIXED):
            introduction_index = next(
                i
                for i, line in enumerate(lines)
                if line.startswith(f"Customer {customer_id} [")
                and line.endswith("introduces customer")
            )
            teller_id = int(lines[introduction_index].split("Teller ")[1].split("]")[0])
            acknowledgment_index = lines.index(
                f"Teller {teller_id} [Customer {customer_id}]: acknowledges customer"
            )
            request_index = lines.index(
                f"Teller {teller_id} [Customer {customer_id}]: asks for transaction"
            )
            supplied_index = lines.index(
                f"Customer {customer_id} [Teller {teller_id}]: "
                f"gives {transaction} transaction"
            )
            completion_index = lines.index(
                f"Teller {teller_id} [Customer {customer_id}]: "
                "informs customer transaction is complete"
            )
            departure_index = lines.index(
                f"Customer {customer_id} [Teller {teller_id}]: leaves the bank"
            )
            finish_index = lines.index(
                f"Teller {teller_id} [Customer {customer_id}]: "
                "finishes serving customer"
            )

            self.assertLess(introduction_index, acknowledgment_index)
            self.assertLess(acknowledgment_index, request_index)
            self.assertLess(request_index, supplied_index)
            self.assertLess(supplied_index, completion_index)
            self.assertLess(completion_index, departure_index)
            self.assertLess(departure_index, finish_index)

    def test_deposits_never_access_manager(self) -> None:
        lines = self.run_bank(DEPOSIT)
        self.assertFalse(any("manager" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is using safe" in line for line in lines))

    def test_withdrawals_use_only_one_manager_at_a_time(self) -> None:
        lines = self.run_bank(WITHDRAWAL)
        active_manager_users = 0
        maximum_manager_users = 0

        for line in lines:
            if "is using manager" in line:
                active_manager_users += 1
                maximum_manager_users = max(maximum_manager_users, active_manager_users)
            elif "is done using manager" in line:
                active_manager_users -= 1
                self.assertGreaterEqual(active_manager_users, 0)

        self.assertEqual(NUM_CUSTOMERS, sum("is going to manager" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is using manager" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is done using manager" in line for line in lines))
        self.assertEqual(0, active_manager_users)
        self.assertEqual(1, maximum_manager_users)

    def test_no_more_than_two_tellers_use_safe_at_once(self) -> None:
        lines = self.run_bank(WITHDRAWAL)
        active_safe_users = 0
        maximum_safe_users = 0

        for line in lines:
            if "is using safe" in line:
                active_safe_users += 1
                maximum_safe_users = max(maximum_safe_users, active_safe_users)
            elif "is done using safe" in line:
                active_safe_users -= 1
                self.assertGreaterEqual(active_safe_users, 0)

        self.assertEqual(NUM_CUSTOMERS, sum("is going to safe" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is using safe" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is done using safe" in line for line in lines))
        self.assertEqual(0, active_safe_users)
        self.assertLessEqual(maximum_safe_users, 2)

    def test_door_occupancy_never_exceeds_two(self) -> None:
        lines = self.run_bank()
        active_door_users = 0
        maximum_door_users = 0
        started_passages = 0
        completed_passages = 0

        for line in lines:
            if "is entering through the door" in line or "is leaving through the door" in line:
                active_door_users += 1
                started_passages += 1
                maximum_door_users = max(maximum_door_users, active_door_users)
            elif line.endswith("enters the bank") or line.endswith("leaves the bank"):
                active_door_users -= 1
                completed_passages += 1
                self.assertGreaterEqual(active_door_users, 0)

        self.assertEqual(NUM_CUSTOMERS * 2, started_passages)
        self.assertEqual(NUM_CUSTOMERS * 2, completed_passages)
        self.assertEqual(0, active_door_users)
        self.assertLessEqual(maximum_door_users, 2)

    def test_tellers_finish_before_serving_their_next_customer(self) -> None:
        lines = self.run_bank()
        active_customer_by_teller: dict[int, int] = {}
        customers_served: Counter[int] = Counter()

        for line in lines:
            started = re.fullmatch(
                r"Teller (\d+) \[Customer (\d+)\]: acknowledges customer", line
            )
            if started:
                teller_id, customer_id = map(int, started.groups())
                self.assertNotIn(teller_id, active_customer_by_teller)
                active_customer_by_teller[teller_id] = customer_id
                customers_served[teller_id] += 1

            finished = re.fullmatch(
                r"Teller (\d+) \[Customer (\d+)\]: finishes serving customer", line
            )
            if finished:
                teller_id, customer_id = map(int, finished.groups())
                self.assertEqual(customer_id, active_customer_by_teller.pop(teller_id))

        self.assertEqual({}, active_customer_by_teller)
        self.assertEqual(set(range(NUM_TELLERS)), set(customers_served))
        self.assertTrue(all(count > 1 for count in customers_served.values()))

    def test_bank_closes_after_customers_leave_and_tellers_stop(self) -> None:
        lines = self.run_bank()
        closing_index = lines.index("Teller 0: the bank is closed")
        leaving_indices = [
            index for index, line in enumerate(lines) if line.endswith("leaves the bank")
        ]
        stopping_indices = [
            index for index, line in enumerate(lines) if line.endswith("stops working")
        ]

        self.assertEqual(NUM_CUSTOMERS, len(leaving_indices))
        self.assertEqual(NUM_TELLERS, len(stopping_indices))
        self.assertTrue(all(index < closing_index for index in leaving_indices))
        self.assertTrue(all(index < closing_index for index in stopping_indices))
        self.assertEqual(len(lines) - 1, closing_index)

    def test_semaphores_and_shared_memory_are_clean_after_shutdown(self) -> None:
        self.run_bank()
        simulation = self.simulation

        self.assertEqual(1, simulation.print_semaphore._value)
        self.assertEqual(1, simulation.state_semaphore._value)
        self.assertEqual(0, simulation.bank_open._value)
        self.assertEqual(2, simulation.door._value)
        self.assertEqual(NUM_TELLERS, simulation.available_teller_count._value)
        self.assertEqual(1, simulation.manager._value)
        self.assertEqual(2, simulation.safe._value)
        self.assertEqual(list(range(NUM_TELLERS)), sorted(simulation.available_tellers))
        self.assertEqual([None] * NUM_TELLERS, simulation.assigned_customers)
        self.assertEqual([None] * NUM_TELLERS, simulation.teller_transactions)

        handshake_semaphores = (
            simulation.customer_arrived
            + simulation.customer_acknowledged
            + simulation.transaction_requested
            + simulation.transaction_supplied
            + simulation.transaction_completed
            + simulation.customer_left
        )
        self.assertTrue(all(semaphore._value == 0 for semaphore in handshake_semaphores))

    def test_every_timed_wait_has_start_and_completion_messages(self) -> None:
        lines = self.run_bank(MIXED)
        self.assertEqual(NUM_CUSTOMERS, sum("begins random wait" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("finishes random wait" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is using safe" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is done using safe" in line for line in lines))

    def test_delay_ranges_and_output_format(self) -> None:
        lines = self.run_bank(MIXED)
        customer_delays = [
            int(match.group(1))
            for line in lines
            if (match := re.search(r"begins random wait for (\d+) milliseconds$", line))
        ]
        manager_delays = [
            int(match.group(1))
            for line in lines
            if (match := re.search(r"is using manager for (\d+) milliseconds$", line))
        ]
        safe_delays = [
            int(match.group(1))
            for line in lines
            if (match := re.search(r"is using safe for (\d+) milliseconds$", line))
        ]
        output_pattern = re.compile(
            r"(?:Customer|Teller) \d+(?: \[(?:Customer|Teller) \d+\])?: .+"
        )

        self.assertEqual(NUM_CUSTOMERS, len(customer_delays))
        self.assertTrue(all(0 <= delay <= 100 for delay in customer_delays))
        self.assertEqual(MIXED.count("Withdrawal"), len(manager_delays))
        self.assertTrue(all(5 <= delay <= 30 for delay in manager_delays))
        self.assertEqual(NUM_CUSTOMERS, len(safe_delays))
        self.assertTrue(all(10 <= delay <= 50 for delay in safe_delays))
        self.assertTrue(all(output_pattern.fullmatch(line) for line in lines))


if __name__ == "__main__":
    unittest.main()
