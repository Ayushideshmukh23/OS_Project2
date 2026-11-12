"""Tests for teller/customer and transaction synchronization."""

from __future__ import annotations

import io
import re
import unittest

from project2 import BankSimulation, NUM_CUSTOMERS, NUM_TELLERS


DEPOSIT = ["Deposit"] * NUM_CUSTOMERS
WITHDRAWAL = ["Withdrawal"] * NUM_CUSTOMERS
MIXED = ["Deposit", "Withdrawal", "Deposit"]


class BankSimulationTests(unittest.TestCase):
    def run_bank(self, transactions: list[str] | None = None) -> list[str]:
        output = io.StringIO()
        simulation = BankSimulation(
            output=output,
            transaction_choices=transactions or MIXED,
            sleep_function=lambda _seconds: None,
        )
        simulation.run()
        self.assertTrue(all(not thread.is_alive() for thread in simulation.threads))
        return output.getvalue().splitlines()

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
            elif "is leaving manager" in line:
                active_manager_users -= 1
                self.assertGreaterEqual(active_manager_users, 0)

        self.assertEqual(NUM_CUSTOMERS, sum("is going to manager" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is using manager" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is leaving manager" in line for line in lines))
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
            elif "is leaving safe" in line:
                active_safe_users -= 1
                self.assertGreaterEqual(active_safe_users, 0)

        self.assertEqual(NUM_CUSTOMERS, sum("is going to safe" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is using safe" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is leaving safe" in line for line in lines))
        self.assertEqual(0, active_safe_users)
        self.assertLessEqual(maximum_safe_users, 2)

    def test_every_timed_wait_has_start_and_completion_messages(self) -> None:
        lines = self.run_bank(MIXED)
        self.assertEqual(NUM_CUSTOMERS, sum("begins random wait" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("finishes random wait" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is using safe" in line for line in lines))
        self.assertEqual(NUM_CUSTOMERS, sum("is leaving safe" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
