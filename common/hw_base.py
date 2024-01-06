"""hw.py: Base class for all HW's"""

import os
import sys
from pathlib import Path
from typing import Callable

from common import printing as p
from common import submissions as subs
from common import utils as u
from common.rubric import Rubric


class HW:
    """Grading Base Class

    Here's a visual representation of some of the fields:
    ~
    \_ .grade
        \_ hwN <---- hw_workspace
           \_ grades.json
           \_ deadline.txt
           \_ hwN <----- submission_dir

    Attributes:
        hw_name: the hw name (in the form 'hwN')
        hw_workspace: Path of the form '~/.grade/hw{1,...,8}', which contains
            the submission_dir, deadline.txt, and grades.json
        scripts_dir: The directory that contains this hw's grading logic.
        rubric: Python representation of the hw rubric
        submission_dir: The student/team's submission directory
            In the above example, this is cloned skeleton code for the
            assignment. We simply pull down teams' tags. In Canvas-based
            assignments, there is 1 submission_dir per student.
    """

    def __init__(self, hw_name, rubric_name):
        self.hw_name = hw_name
        self.hw_workspace = os.path.join(
            Path.home(), ".grade", os.getenv("TA", default=""), hw_name
        )

        # Find grader root relative to hw_base.py: root/common/hw_base.py
        pygrader_root = Path(__file__).resolve().parent.parent

        self.scripts_dir = os.path.join(pygrader_root, self.hw_name)

        # Here we assume the rubric file is in the scripts dir.
        self.rubric = Rubric(os.path.join(self.scripts_dir, rubric_name))

        self.submission_dir = None  # Populated in subclasses.

        self.ran_rubric_item_codes = set()
        self.ran_rubric_tests = set()

    def do_cd(self, path):
        """Changes directory relative to the self.submission_dir.

        For example, if you had the following:
            hw3  <---- self.submission_dir
            \_ part1
               \_ part1-sub

        and you wanted to cd into part1-sub, you would run
        `do_cd(os.path.join('part1', 'part1-sub'))`.
        """
        part_dir = os.path.join(self.submission_dir, path)
        u.is_dir(part_dir)
        os.chdir(part_dir)

    def exit_handler(self, _signal, _frame):
        """Handler for SIGINT

        Note: this serves as a template for how the subclasses should do it.
        The subclass is free to override this function with more hw-specific
        logic.
        """
        p.print_cyan("\n[ Exiting generic grader... ]")
        self.cleanup()
        sys.exit()

    def check_late_submission(self):
        """Grabs the latest commit timestamp to compare against the deadline"""
        proc = u.cmd_popen("git log -n 1 --format='%aI'")
        iso_timestamp, _ = proc.communicate()

        return subs.check_late(
            os.path.join(self.hw_workspace, "deadline.txt"), iso_timestamp.strip("\n")
        )

    def default_grader(self):
        """Generic grade function."""
        p.print_red("[ Opening shell, ^D/exit when done. ]")
        os.system("bash")

    def setup(self):
        """Performs submission setup (e.g. untar, git checkout tag)."""

    def cleanup(self):
        """Performs cleanup (kills stray processes, removes mods, etc.)."""


def directory(start_dir: str) -> Callable:
    """Decorator function that cd's into `start_dir` before the test.

    If start_dir is 'root', we cd into the root of the submission_dir.
    For example:
        @directory("part1")
        def test_B1(self):
            ...
    This will cd into submission_dir/part1 before calling test_B1().
    """

    # This is definitely overkill, but for ultimate correctness (and
    # for the sake of making the decorator usage sleek), let's allow
    # users to just use '/'. We can correct it here.
    start_dir = os.path.join(*start_dir.split("/"))

    def function_wrapper(test_func):
        def cd_then_test(hw_instance):
            try:
                hw_instance.do_cd("" if start_dir == "root" else start_dir)
            except ValueError:
                p.print_red(
                    "[ Couldn't cd into tester's @directory, " "opening shell.. ]"
                )
                os.system("bash")
            return test_func(hw_instance)

        return cd_then_test

    return function_wrapper
