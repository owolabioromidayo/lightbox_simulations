import os, sys, json, random, base64, time, copy, requests, datetime, threading
from flask import Flask, request
# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address

import heapq

app = Flask(__name__)

TRUST_SCORE_UPDATE = 40
TRUST_SCORE_RESET_PVE_HRS = 24
TRUST_SCORE_RESET_NVE_HRS = 48
GPU_TASK_SLEEP_TIME = 5
FEDERATED_TRUST_SCORE = 400

GPU_WORKERS = None
LOGFILE= None

def log_to_file(str):
    
    str += '\n'
    # print(LOGFILE)
    fname = LOGFILE
    if os.path.isfile(fname):
        with open(fname, 'a' ) as f:
            f.write(str)
        return 
    else:
        with open(fname, 'w' ) as f:
            f.write(str)


class PriorityQueue:
    def __init__(self):
        self._queue = []
        self._index = 0

    def push(self, item, priority):
        heapq.heappush(self._queue, (-priority, self._index, item))
        self._index += 1

    def pop(self):
        return heapq.heappop(self._queue)[-1]

    def __len__(self):
        return len(self._queue)


workers = dict()
work_queue = dict()
work_returns = dict()


# limiter = Limiter(
#     get_remote_address,
#     app=app,
#     default_limits=["100 per minute"],
#     storage_uri="memory://",
#     strategy="fixed-window", # or "moving-window"
# )


#we need the thread that acts on the queue information. normally we have
#individual gpu workers checking for tasks. we can do that

def gpu_worker_thread(id):
    #initialization
    # workers[id] = {"in_use": False}
    work_queue[id] = PriorityQueue()

    while True:
        #check if task
        if len(work_queue[id]) > 0:
            new_task = work_queue[id].pop() #pop and execute highest priority task
            # print(f" Sending new task", new_task) 
            time.sleep(GPU_TASK_SLEEP_TIME)
            work_returns[new_task["timestamp"]] = 1 #populate work returns

        else:
            time.sleep(1) #sleep some more if no task
       
        time.sleep(2)  #sleep


# print(workers)
# print(work_queue[1])

@app.route("/federated/execute_task/<_id>", methods=["GET","POST"])
def exec_federated_task(_id):

    _id = int(_id)

    timestamp = time.time()
    work_queue[_id].push({"timestamp": timestamp}, FEDERATED_TRUST_SCORE)
    work_returns[timestamp] = None

    while work_returns[timestamp] == None:
        time.sleep(5)
        continue

    # if work_returns[timestamp] == "Failed":
    #     return "Task was aborted by GPU client", 500
    
    # _response = work_returns[timestamp]
    del work_returns[timestamp]
    return "Done!", 200


@app.route("/make_federated_request/<secondary>/<_id>", methods=["GET","POST"])
def query_federated_server(secondary, _id):
   
    _json = request.json
    _id = int(_id)

    _start = datetime.datetime.now()

    trust_score = _json["trust_score"]
    last_update_time = _json["last_update_time"]
    user_id = _json['user_id']
    user_count = _json['user_count']
    task_count = _json['task_count']
    trust_score = _json["trust_score"]
    # last_update_time = _json["last_update_time"]
    # user_id = _json['user_id']
    
    last_update_time = datetime.datetime.fromtimestamp(last_update_time)

    time_delta = datetime.datetime.utcnow() - last_update_time 
    hours_delta = time_delta / datetime.timedelta(hours=1)

    if trust_score > 0 and hours_delta >= TRUST_SCORE_RESET_PVE_HRS:
        trust_score = 1000

    if trust_score <= 0 and hours_delta >= TRUST_SCORE_RESET_NVE_HRS:
        trust_score = 1000
      
    if trust_score <= 0:
        _response = {"trust_score" : trust_score, "last_update_time": datetime.datetime.utcnow().timestamp()}
        log_to_file(f"{str(datetime.datetime.now())} /make_federated_request {user_count} {(datetime.datetime.now() - _start).seconds} {user_id} {_id} {trust_score} {task_count}")
        return  {"data" : _response}

    _url = f"http://localhost:{secondary}"

    #make federated request to server
    response = requests.get(f"{_url}/federated/execute_task/{_id}")
    _response = {"trust_score" : trust_score, "last_update_time": datetime.datetime.utcnow().timestamp()}

    log_to_file(f"{str(datetime.datetime.now())} /make_federated_request {user_count} {(datetime.datetime.now() - _start).seconds} {user_id} {_id} {trust_score} {task_count}")
    if response.status_code == 200:
        return {"data" : _response}
    else:
        return {"data" : _response}
        # return "Request failed", response.status_code


@app.route("/execute_task/<_id>", methods=["GET","POST"])
def exec_task(_id):
    
    _start = datetime.datetime.now()

    _json = request.json
    _id = int(_id)

    trust_score = _json["trust_score"]
    last_update_time = _json["last_update_time"]
    user_id = _json['user_id']
    user_count = _json['user_count']
    task_count = _json['task_count']

    last_update_time = datetime.datetime.fromtimestamp(last_update_time)

    #check trust score and last update time
    time_delta = datetime.datetime.utcnow() - last_update_time 
    hours_delta = time_delta / datetime.timedelta(hours=1)

    if trust_score > 0 and hours_delta >= TRUST_SCORE_RESET_PVE_HRS:
        trust_score = 1000

    if trust_score <= 0 and hours_delta >= TRUST_SCORE_RESET_NVE_HRS:
        trust_score = 1000
      
         
    if trust_score <= 0:
        _response = {"trust_score" : trust_score, "last_update_time": datetime.datetime.utcnow().timestamp()}
        log_to_file(f"{str(datetime.datetime.now())} /exec_task {user_count} {(datetime.datetime.now() - _start).seconds} {user_id} {_id} {trust_score} {task_count}")
        return  {"data" : _response}


    timestamp = time.time()
    work_queue[_id].push({"timestamp": timestamp}, trust_score)
    # print([len(work_queue[i]) for i in range(10) ])
    work_returns[timestamp] = None

    while work_returns[timestamp] == None:
        time.sleep(5)
        continue


    # if work_returns[timestamp] == "Failed":
    #     return "Task was aborted by GPU client", 500
    
    trust_score -= TRUST_SCORE_UPDATE #trust score update

    _response = {"trust_score" : trust_score, "last_update_time": datetime.datetime.utcnow().timestamp()}

    del work_returns[timestamp]

    log_to_file(f"{str(datetime.datetime.now())} /exec_task {user_count} {(datetime.datetime.now() - _start).seconds} {user_id} {_id} {trust_score} {task_count}")

    return  {"data" : _response}


if __name__ == "__main__":
    port = sys.argv[1]
    GPU_WORKERS  = int(sys.argv[2])
    USER_COUNT= int(sys.argv[3])
    LOGFILE = f'log_baseline_{USER_COUNT}_{GPU_WORKERS}_multiple_{random.randrange(112)}'

    for i  in range(GPU_WORKERS):
        thread = threading.Thread(target=gpu_worker_thread, args=(i,))
        thread.start()

    app.run(debug=True, port=port) 









    
