from ui import NOVAUI


def create_assistant():
    """Import voice services only after the window is already responsive."""
    from assistant import NOVA
    return NOVA()


def main():
    NOVAUI(assistant_factory=create_assistant).run()


if __name__ == "__main__":
    main()
    
 