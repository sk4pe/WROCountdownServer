#!/usr/bin/env python

import asyncio
import datetime
import websockets
from websockets import ConnectionClosed


ip_adresse = '10.19.135.255'
port = 8000
#cdrunning={'Dortmund':False, 'Hannover':False}
#connected = {'Dortmund':[], 'Hannover':[]}
#cdFinish={'Dortmund':None,'Hannover':None}
cdrunning = {}
connected = {}
cdFinish = {}



print(str(datetime.datetime.now()+datetime.timedelta(0,1))+": Server started")

async def time(websocket):
    while True:
        await asyncio.sleep(10)

        for loc_id in cdrunning:
            if websocket in connected[loc_id] and await getCDStatus(websocket):


                secondsLeft = (cdFinish[loc_id]-datetime.datetime.now()).total_seconds()
                if secondsLeft <= 0:
                    cdrunning[loc_id]=False

                return str(int(secondsLeft))





async def handleIncomingMessage(msg,websocket):
    print(str(datetime.datetime.now() + datetime.timedelta(0, 1)) +": "+ msg)
    incomingMsg = str(msg).split(' ')
    global cdrunning
    global connected

    if incomingMsg[0] == 'start' and incomingMsg[1] == 'countdown':
        if not cdrunning[incomingMsg[2]]:
            cdrunning[incomingMsg[2]] = True
            cdDuration = incomingMsg[3]
            cdFinish[incomingMsg[2]]=datetime.datetime.now()+datetime.timedelta(0,int(cdDuration))

            for socket in connected[incomingMsg[2]]:

                await sendMsg(socket,'start ' + str(int(cdDuration)))

    elif incomingMsg[0] == 'stop' and incomingMsg[1] == 'countdown':
        if cdrunning[incomingMsg[2]]:
            cdrunning[incomingMsg[2]] = False
            for socket in connected[incomingMsg[2]]:
                await sendMsg(socket,'stop')
    elif incomingMsg[0] == 'connection' and incomingMsg[1] == 'from':
        location = incomingMsg[2]
        if location not in connected:
            connected[location] = []

        connected[location].append(websocket)
        if location in cdrunning:

            if cdrunning[location]:
                cdLeft = (cdFinish[location] - datetime.datetime.now()).total_seconds()
                await sendMsg(websocket, 'start ' + str(int(cdLeft)))
        else:
            cdrunning[location] = False
            cdFinish[location]=0




async def producer_handler(websocket, path):
    while True:

        message = await time(websocket)
        if await getCDStatus(websocket):

            await sendMsg(websocket,'sync ' + message)



async def sendMsg(websocket, msg):
    print(str(datetime.datetime.now() + datetime.timedelta(0, 1)) + ": "+ msg)
    await websocket.send(msg)

async def getCDStatus(websocket):
    global cdrunning
    global connected
    loc = ''
    for location in connected:

        if websocket in connected[location]:

            loc = location

    if loc == '':
        return False
    else:
        return cdrunning[loc]

async def consumer_handler(websocket, path):
    while True:
        try:
            message = await websocket.recv()

        except ConnectionClosed:
            websocket.close()
            await clearConnection(websocket)

            break

        await handleIncomingMessage(message,websocket)

async def clearConnection(websocket):
    for loc in connected:

        if websocket in connected[loc]:


            connected[loc].remove(websocket)
            print(str(datetime.datetime.now() + datetime.timedelta(0, 1)) + ': client from  ' + loc + ' disconnected')

            break
async def handler(websocket, path):



    consumer_task = asyncio.ensure_future(consumer_handler(websocket,path))
    producer_task = asyncio.ensure_future(producer_handler(websocket,path))
    done, pending = await asyncio.wait(
        [consumer_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

start_server = websockets.serve(handler, ip_adresse, port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()