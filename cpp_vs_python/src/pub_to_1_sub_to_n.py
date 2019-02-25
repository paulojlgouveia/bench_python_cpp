
import sys, os
import time
from subprocess import Popen, PIPE, STDOUT
from time import sleep
from signal import pause

from argparse import ArgumentParser, ArgumentError
from datetime import timedelta
from time import sleep

from multiprocessing import Pool, Process
from threading import Thread, Lock
from _thread import interrupt_main

from aeronpy import Context, BACK_PRESSURED, NOT_CONNECTED, ADMIN_ACTION, PUBLICATION_CLOSED


def endOfStream(args):
    return None

def processData(args):
    return None


def subscriber(args):
    context = Context(
        aeron_dir=args.prefix,
        resource_linger_timeout=timedelta(milliseconds=args.linger),
        # new_publication_handler=lambda *args: print(f'new publication - {args}'),
        # new_subscription_handler=lambda *args: print(f'new subscription {args}'),
        # available_image_handler=lambda *args: print(f'available image {args}'),
        # unavailable_image_handler = lambda *args: print(f'unavailable image {args}')
    )
    subscriptions = []

    for id in range(0, args.processes):
        subscriptions.append(context.add_subscription(args.channel, id+1))

    while True:
        for sub in subscriptions:

            # fragments_read = sub.poll(lambda data: print(bytes(data)))
            fragments_read = sub.poll(processData)

            if fragments_read == 0:
                # eos_count = sub.poll_eos(lambda *args: print(f'end of stream: {args}'))
                eos_count = sub.poll_eos(endOfStream)
                if eos_count > 0:
                    return 0


def publisher(streamID, messages, args):

    context = Context(
        aeron_dir=args.prefix,
        resource_linger_timeout=timedelta(milliseconds=args.linger),
        # new_publication_handler=lambda *args: print(f'new publication - {args}'),
        # new_subscription_handler=lambda *args: print(f'new subscription {args}'),
        # available_image_handler=lambda *args: print(f'available image {args}'),
        # unavailable_image_handler = lambda *args: print(f'unavailable image {args}')
    )


    publication = context.add_publication(args.channel, streamID)
    for msg in messages:

        # sleep(0.001)
        result = publication.offer(msg)

        # if result == BACK_PRESSURED:
        #     print('Offer failed due to back pressure')
        #
        # elif result == NOT_CONNECTED:
        #     print('Offer failed because publisher is not connected to subscriber')
        #
        # elif result == ADMIN_ACTION:
        #     print('Offer failed because of an administration action in the system')
        #
        # elif result == PUBLICATION_CLOSED:
        #     print('Offer failed publication is closed')

        # else:
        #     print('yay!')


    # print("done.")
    return 0



def main(args):

    try:
        parser = ArgumentParser()
        parser.add_argument('-p', '--prefix', default=None)
        parser.add_argument('-c', '--channel', default='aeron:udp?endpoint=localhost:40123')
        parser.add_argument('-s', '--stream_id', type=int, default=1)
        parser.add_argument('-m', '--messages', type=int, default=10000)
        parser.add_argument('-l', '--linger', type=int, default=60*60*1000)
        parser.add_argument('-k', '--processes', type=int, default=4)

        args = parser.parse_args()
        context = Context(
            aeron_dir=args.prefix,
            resource_linger_timeout=timedelta(milliseconds=args.linger),
            # new_publication_handler=lambda *args: print(f'new publication - {args}'),
            # new_subscription_handler=lambda *args: print(f'new subscription {args}'),
            # available_image_handler=lambda *args: print(f'available image {args}'),
            # unavailable_image_handler = lambda *args: print(f'unavailable image {args}')
        )

        messages = []
        for i in range(args.messages):
            messages.append(bytearray(os.urandom(256)))

        start = time.time()

        publishers = []
        for streamID in range(1, args.processes+1):
            publishers.append(Process(target=publisher, args=(streamID, messages, args,)))

        subscribers = []
        for streamID in range(1, args.processes+1):
            publishers.append(Process(target=subscriber, args=(args,)))

        for p in publishers:
            p.start()

        for p in subscribers:
            p.start()

        for p in publishers:
            p.join()

        for p in subscribers:
            p.join()
            # p.terminate()

        for p in subscribers:
            p.join()


        end = time.time()
        print(str(end - start))


    except ArgumentError as e:
        print(e, file=sys.stderr)
        return -1

    except Exception as e:
        print(e, file=sys.stderr)
        return -2




if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("arguments")
        print(" * " + sys.argv[0] + "-c -m -k ")
        sys.exit()

    elif len(sys.argv) > 2:
        main(sys.argv)
