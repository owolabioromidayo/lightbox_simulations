import os, threading, time, sys

# PORTS = [3006, 3007, 3008]

if __name__ == "__main__":
    PORTS =  [3006, 3007, 3008, 3009]

    SIM_TIME = 6.7 * 60

    USER_COUNT = int(sys.argv[1])
    GPU_COUNT = int(USER_COUNT / 10)

    USER_COUNT *= 4



    SERVER_COUNT = len(PORTS)

    commands = []

    for i in range(SERVER_COUNT):
        commands.append(f"python3 server.py {PORTS[i]} {GPU_COUNT} {USER_COUNT} ")

    def command_thread(i):
        os.system(commands[i])


    for i in range(len(commands)):
        thread = threading.Thread(target=command_thread, args=(i,))
        thread.start()


    time.sleep(20)
    os.system(f"python3 user_gen.py {USER_COUNT} {GPU_COUNT}")
    time.sleep(SIM_TIME + 10)
    sys.exit()

