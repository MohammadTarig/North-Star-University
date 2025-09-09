# memory.py


class ChatMemory:
    """
    Simple memory to store chat messages and retrieve them.
    """

    def __init__(self):
        self.messages = []

    def add_message(self, role, content):
        """
        Add a message to memory.
    
        """
        self.messages.append({"role": role, "content": content})

    def get_all_messages(self):
        """
        Return all stored messages in order.
        """
        return self.messages

    def reset_memory(self):
        """
        Clear all stored messages.
        """
        self.messages = []


# ---- Example usage ----
if __name__ == "__main__":
    memory = ChatMemory()
    memory.add_message("user", "I don't understand this question.")
    memory.add_message("bot", "Let's break it down step by step.")

    print("All messages:")
    for msg in memory.get_all_messages():
        print(f"{msg['role']}: {msg['content']}")

    # Reset memory
    memory.reset_memory()
    print("\nAfter reset:", memory.get_all_messages())  # Should be empty list
