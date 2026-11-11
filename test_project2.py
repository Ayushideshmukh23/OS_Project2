"""Tests for the first teller/customer synchronization milestone."""

import io
import re
import unittest

from project2 import BankSimulation, NUM_CUSTOMERS, NUM_TELLERS


class BankSimulationTests(unittest.TestCase):
    def run_bank(self) -> list[str]:
        output = io.StringIO()
        BankSimulation(output=output).run()
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

    def test_acknowledgment_precedes_departure_and_teller_finishes_last(self) -> None:
        lines = self.run_bank()

        for customer_id in range(NUM_CUSTOMERS):
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
            departure_index = lines.index(
                f"Customer {customer_id} [Teller {teller_id}]: leaves the bank"
            )
            finish_index = lines.index(
                f"Teller {teller_id} [Customer {customer_id}]: finishes serving customer"
            )

            self.assertLess(introduction_index, acknowledgment_index)
            self.assertLess(acknowledgment_index, departure_index)
            self.assertLess(departure_index, finish_index)


if __name__ == "__main__":
    unittest.main()
