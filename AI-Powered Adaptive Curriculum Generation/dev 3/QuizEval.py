import os
import json
import random
from questionsGen import questionsToJson


def get_valid_input(prompt, choices):
    """Ask for user input until a valid letter is entered."""
    while True:
        ans = input(prompt).upper().strip()
        if ans in choices:
            return ans
        print(f"Invalid input, please choose from {', '.join(choices)}")


class AdaptiveQuiz:
    def __init__(self, assessments):
        self.levels = ["easy", "medium", "hard"]
        self.assessments = {
            lvl: random.sample(assessments[lvl], len(assessments[lvl]))
            for lvl in self.levels
        }
        self.progress = {
            lvl: 0 for lvl in self.levels
        }  
        self.total_correct = {
            lvl: 0 for lvl in self.levels
        }  
        self.current_level = "easy"

        self.current_round_correct = 0
        self.current_round_wrong = 0

        self.failed = False

        self.transitions = {
            "easy": {"up": "medium", "down": None},
            "medium": {"up": "hard", "down": "easy"},
            "hard": {"up": "hard", "down": "medium"},
        }

    def ask_question(self):
        idx = self.progress[self.current_level]
        if idx >= len(self.assessments[self.current_level]):
            return None  

        q = self.assessments[self.current_level][idx]
        options = dict(zip("ABCD", q["options"]))

        print(
            f"\n--- Current level: {self.current_level.upper()} "
            f"(Question {idx + 1} of {len(self.assessments[self.current_level])}) ---"
        )
        print(q["question"])
        for k, v in options.items():
            print(f"{k}. {v}")

        ans = get_valid_input("Your answer (A/B/C/D): ", "ABCD")
        chosen_answer = options[ans]

        correct = chosen_answer == q["answer"]
        if correct:
            print("✅ Correct!")
        else:
            print(f"❌ Wrong! Correct answer: {q['answer']}")

        self.progress[self.current_level] += 1
        return correct

    def run(self):
        while True:
            result = self.ask_question()
            if result is None:
                break

            if result:
                self.current_round_correct += 1
                self.total_correct[self.current_level] += 1
            else:
                self.current_round_wrong += 1

            if self.current_round_correct == 3:

                if self.current_level == "hard":
                    print(f"🎯 3 correct in HARD! You’re doing great, keep going!")
                    self.current_round_correct = 0
                    continue

                next_level = self.transitions[self.current_level]["up"]
                print(f"🎯 3 correct in {self.current_level.upper()}! Advancing to {next_level.upper()}.")
                self.current_level = next_level

                self.current_round_correct = 0
                self.current_round_wrong = 0
                continue

            if self.current_round_wrong == 2:
                correct_before_drop = self.current_round_correct
                self.progress[self.current_level] += correct_before_drop

                next_level = self.transitions[self.current_level]["down"]
                if next_level is None:
                    print("❌ Two wrongs in EASY level. Test failed.")
                    self.failed = True
                    break
                else:
                    print(f"⬇️ Two wrongs in {self.current_level.upper()} → Dropping to {next_level.upper()}")
                    self.current_level = next_level

                    self.current_round_correct = 0
                    self.current_round_wrong = 0
                    continue

            if self.progress[self.current_level] >= len(
                self.assessments[self.current_level]
            ):
                print(f"🏁 No more questions in {self.current_level.upper()} level.")
                break

        return self.get_feedback()

    def get_feedback(self):
        if self.failed:
            correct_count = self.total_correct[self.current_level]
            total_q = len(self.assessments[self.current_level])
            return (
                "failed",
                f"You failed early. Please review all material carefully. ({correct_count}/{total_q} correct)",
            )
        if (
            self.progress["hard"] >= len(self.assessments["hard"])
            or self.current_level == "hard"
        ):
            correct_count = self.total_correct["hard"]
            total_q = len(self.assessments["hard"])
            if correct_count <= 5:
                return (
                    "hard",
                    f"🌟 Excellent work! You reached hard level and Passed the Medium level. ({correct_count}/{total_q} correct) But you can do better",
                )
            else:
                return (
                    "hard",
                    f"🌟 Excellent work! You reached hard level. ({correct_count}/{total_q} correct) You have passed the test",
                )
        elif (
            self.progress["medium"] >= len(self.assessments["medium"])
            or self.current_level == "medium"
        ):
            correct_count = self.total_correct["medium"]
            total_q = len(self.assessments["medium"])
            if correct_count <= 5:
                return (
                    "medium",
                    f"🌟 Excellent work! You reached medium level. ({correct_count}/{total_q} correct) But you can do better",
                )
            else:
                return (
                    "medium",
                    f"🌟 Excellent work! You reached medium level. ({correct_count}/{total_q} correct) You have passed the medium level, Work on the hard level",
                )
        else:
            correct_count = self.total_correct["easy"]
            total_q = len(self.assessments["easy"])
            if correct_count <= 5:
                return (
                    "easy",
                    f"🌟 Excellent work! You reached easy level and Passed the Medium level. ({correct_count}/{total_q} correct) But you can do better",
                )
            else:
                return (
                    "easy",
                    f"🌟 Excellent work! You reached easy level. ({correct_count}/{total_q} correct) You have passed the easy level, Work on the medium level",
                )


if __name__ == "__main__":
    filename = questionsToJson()
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)

    quiz = AdaptiveQuiz(data["assessments"])
    result_level, feedback = quiz.run()

    print("\n=== Assessment Finished ===")
    print(f"Result Level: {result_level.upper()}")
    print(f"Feedback: {feedback}")
