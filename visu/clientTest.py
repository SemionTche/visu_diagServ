import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:1230")

# send message to get answer
socket.send_string("__GET__")

reply = socket.recv_string()
print("Server answer:", reply)
