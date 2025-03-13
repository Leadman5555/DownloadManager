from colorama import Fore, Style


class MessageHandler:
    @staticmethod
    def debug(msg):
        if msg.startswith('[debug] '):
            pass
        else:
            MessageHandler.info(msg)
        pass

    @staticmethod
    def info(msg):
        print(Style.RESET_ALL + f"[INFO] {msg}")

    @staticmethod
    def warning(msg):
        pass

    @staticmethod
    def error(msg):
        print(Fore.RED + f"[ERROR] {msg}" + Style.RESET_ALL)

    @staticmethod
    def success(msg):
        print(Fore.GREEN + f"[SUCCESS] {msg}" + Style.RESET_ALL)

    @staticmethod
    def banner(msg):
        print(Fore.CYAN + f" ########## {msg} #########\n" + Style.RESET_ALL)

    @staticmethod
    def receive_input(msg):
        return input(Style.RESET_ALL + msg)