from colorama import Fore, Style


class MessageHandler:
    @staticmethod
    def debug(msg):
        if msg.startswith('[debug] '):
            pass
        else:
            MessageHandler.info(msg)

    @staticmethod
    def info(msg):
        print(Style.RESET_ALL + f"[INFO] {msg}")

    @staticmethod
    def error(msg):
        print(Fore.RED + f"[ERROR] {msg}")

    @staticmethod
    def success(msg):
        print(Fore.GREEN + f"[SUCCESS] {msg}")

    @staticmethod
    def banner(msg):
        print(Fore.CYAN + f" ########## {msg} #########\n")

    @staticmethod
    def receive_input(msg):
        return input(Style.RESET_ALL + msg)