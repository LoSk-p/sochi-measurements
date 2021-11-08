import matplotlib.pyplot as plt
from datetime import datetime, timedelta

datas = []
data = []
with open("data/02.11_geyger.txt") as f:
    for line in f:
        if line[0] != "S" and len(line) > 1:
            data.append(float(line.split()[1])*0.00812)
        if line[0] == "S":
            datas.append(data)
            data = []

datas = datas[1:-9]
# print(datas)
start_data = datetime(2021, 11, 2, 9, 00)
times = []
for data in datas:
    time = [start_data + timedelta(seconds=145*i) for i in range(len(data))]
    times.append(time)
    # print(time)
    start_data = time[-1]
print("datas")
print(datas)
print("times")
print(times)

for i in range(len(datas)):
    print(datas[i])
    plt.figure(i)
    plt.plot(times[i], datas[i])
    plt.savefig(f'images/geiger{i}')


plt.figure(len(datas))
for i in range(len(datas)):
    plt.plot(times[i], datas[i])

plt.legend(['shale', 'shale', 'shale', 'mountain', 'waterfall'])
plt.savefig(f'images/geiger')