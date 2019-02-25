
#include <cstdint>
#include <cstdio>
#include <signal.h>
#include <time.h>
#include <stdlib.h>
#include <iomanip>
#include <util/CommandOptionParser.h>
#include <thread>
#include <Aeron.h>
#include <array>
#include <concurrent/BusySpinIdleStrategy.h>
#include "Configuration.h"
#include "RateReporter.h"
#include "FragmentAssembler.h"

#define __STDC_FORMAT_MACROS
#include <inttypes.h>

using namespace aeron::util;
using namespace aeron;

std::atomic<bool> running (true);

inline bool isRunning() {
    return std::atomic_load_explicit(&running, std::memory_order_relaxed);
}


void sigIntHandler (int param)
{
    running = false;
}

static const char optHelp     = 'h';
static const char optPrefix   = 'p';
static const char optChannel  = 'c';
static const char optStreamId = 's';
static const char optMessages = 'm';
static const char optLinger   = 'l';
static const char optLength   = 'L';
static const char optProgress = 'P';
static const char optFrags    = 'f';

static const char optProcess  = 'k';

static const std::chrono::duration<long, std::milli> IDLE_SLEEP_MS(1);
static const int FRAGMENTS_LIMIT = 10;


struct Settings {
    std::string dirPrefix = "";
    std::string channel = samples::configuration::DEFAULT_CHANNEL;
    std::int32_t streamId = samples::configuration::DEFAULT_STREAM_ID;
    long numberOfMessages = samples::configuration::DEFAULT_NUMBER_OF_MESSAGES;
    int messageLength = samples::configuration::DEFAULT_MESSAGE_LENGTH;
    int lingerTimeoutMs = samples::configuration::DEFAULT_LINGER_TIMEOUT_MS;
    int fragmentCountLimit = samples::configuration::DEFAULT_FRAGMENT_COUNT_LIMIT;
    bool progress = samples::configuration::DEFAULT_PUBLICATION_RATE_PROGRESS;

    int processes = 4;
};

typedef std::array<std::uint8_t, 256> buffer_t;


Settings parseCmdLine(CommandOptionParser& cp, int argc, char** argv) {
    cp.parse(argc, argv);
    if (cp.getOption(optHelp).isPresent()) {
        cp.displayOptionsHelp(std::cout);
        exit(0);
    }

    Settings s;

    s.dirPrefix = cp.getOption(optPrefix).getParam(0, s.dirPrefix);
    s.channel = cp.getOption(optChannel).getParam(0, s.channel);
    s.streamId = cp.getOption(optStreamId).getParamAsInt(0, 1, INT32_MAX, s.streamId);
    s.numberOfMessages = cp.getOption(optMessages).getParamAsLong(0, 0, LONG_MAX, s.numberOfMessages);
    s.messageLength = cp.getOption(optLength).getParamAsInt(0, sizeof(std::int64_t), INT32_MAX, s.messageLength);
    s.lingerTimeoutMs = cp.getOption(optLinger).getParamAsInt(0, 0, 60 * 60 * 1000, s.lingerTimeoutMs);
    s.fragmentCountLimit = cp.getOption(optFrags).getParamAsInt(0, 1, INT32_MAX, s.fragmentCountLimit);
    s.progress = cp.getOption(optProgress).isPresent();

    s.processes = cp.getOption(optProcess).getParamAsInt(0, 1, INT32_MAX, s.processes);

    return s;
}

std::atomic<bool> printingActive;

void printRate(double messagesPerSec, double bytesPerSec, long totalFragments, long totalBytes) {
    if (printingActive) {
        std::printf(
            "\n%.02g msgs/sec, %.02g bytes/sec, totals %ld messages %ld MB payloads\n",
            messagesPerSec, bytesPerSec, totalFragments, totalBytes / (1024 * 1024));
    }
}

fragment_handler_t rateReporterHandler(RateReporter& rateReporter) {
    return [&rateReporter](AtomicBuffer&, util::index_t, util::index_t length, Header&) {
        rateReporter.onMessage(1, length);
    };
}

fragment_handler_t printStringMessage() {
    return [&](const AtomicBuffer& buffer, util::index_t offset, util::index_t length, const Header& header) {
//        std::cout << " [" << header.sessionId();
//        std::cout << " (" << length << "@" << offset << ")] - ";
//        std::cout << std::string(reinterpret_cast<const char *>(buffer.buffer()) + offset, static_cast<std::size_t>(length)) << std::endl;
    };
}

void printEndOfStream(Image &image) { }




void generateMsg(char *msg, const int msgLength) {
    static const char alphanum[] =
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz";

    for (int i = 0; i < msgLength; i++) {
        msg[i] = alphanum[rand() % (sizeof(alphanum) - 1)];
        msg[msgLength-1] = 0;
    }
}



int main(int argc, char **argv) {
    CommandOptionParser cp;
    cp.addOption(CommandOption (optHelp,     0, 0, "                Displays help information."));
    cp.addOption(CommandOption (optProgress, 0, 0, "                Print rate progress while sending."));
    cp.addOption(CommandOption (optPrefix,   1, 1, "dir             Prefix directory for aeron driver."));
    cp.addOption(CommandOption (optChannel,  1, 1, "channel         Channel."));
    cp.addOption(CommandOption (optStreamId, 1, 1, "streamId        Stream ID."));
    cp.addOption(CommandOption (optMessages, 1, 1, "number          Number of Messages."));
    cp.addOption(CommandOption (optLength,   1, 1, "length          Length of Messages."));
    cp.addOption(CommandOption (optLinger,   1, 1, "milliseconds    Linger timeout in milliseconds."));
    cp.addOption(CommandOption (optFrags,    1, 1, "limit           Fragment Count Limit."));

    cp.addOption(CommandOption (optProcess,  1, 1, "processes       Processes Limit."));

    signal (SIGINT, sigIntHandler);



    try {
        // setup
        Settings settings = parseCmdLine(cp, argc, argv);

        aeron::Context context;
        Aeron aeron(context);

        BusySpinIdleStrategy offerIdleStrategy;
        BusySpinIdleStrategy pollIdleStrategy;

        fragment_handler_t handler = printStringMessage();
        SleepingIdleStrategy idleStrategy(IDLE_SLEEP_MS);


        // generate messages
        srand(time(NULL));
//        char msgArray[settings.numberOfMessages][settings.messageLength];
//        for (int i = 0; i < settings.numberOfMessages; i++) {
//            generateMsg(msgArray[i], settings.messageLength);
//        }
        const int MSG_COUNT = 10000, MSG_LEN = 256;
        char msgArray[MSG_COUNT][MSG_LEN];
        for (int i = 0; i < MSG_COUNT; i++) {
            generateMsg(msgArray[i], MSG_LEN);
        }

        if (settings.dirPrefix != "") {
            context.aeronDir(settings.dirPrefix);
        }

//        const clock_t begin_time = clock();
        struct timespec start, finish;

        clock_gettime(CLOCK_MONOTONIC, &start);


        // threads corresponding to each theoretical process
        std::vector<std::thread> workers;

        for (int streamId = 1; streamId <= settings.processes; streamId++) {
            workers.push_back( std::thread([&msgArray, &MSG_COUNT, &aeron, &pollIdleStrategy, &settings, &handler, streamId]() {

                int k = 0;

                //publish self
                std::int64_t publicationId = aeron.addPublication(settings.channel, streamId);

                // wait for the publication to be valid
                std::shared_ptr<Publication> publication = aeron.findPublication(publicationId);
                while (!publication) {
                    std::this_thread::yield();
                    publication = aeron.findPublication(publicationId);
                }
//                std::cout << "publishing to " << settings.channel << " on Stream ID " << publicationId << std::endl;


                // subscribe to all other channels
                std::vector<std::int64_t> subscriptionIds;
                for (k = 1; k <= settings.processes; k++) {
                    subscriptionIds.push_back(aeron.addSubscription(settings.channel, k));
                }

                // populate subscriptions hashmap
                std::shared_ptr<Subscription> sub;
                std::vector<std::shared_ptr<Subscription>> subscriptions;
                for (k = 0; k < settings.processes; k++) {
                    sub = aeron.findSubscription(subscriptionIds[k]);
                    while (!sub) {
                        std::this_thread::yield();
                        sub = aeron.findSubscription(subscriptionIds[k]);
                    }

                    subscriptions.push_back(sub);
//                    std::cout << "subscribed to " << settings.channel << " on Stream ID " << subscriptionIds[k] << std::endl;
                }

                // define subscription behaviour
                std::thread pollThread = std::thread([&subscriptions, &pollIdleStrategy, &settings, &handler]() {
                    int t = 0;
                    bool reachedEos = false;

                    while (isRunning()) {
                        int fragmentsRead;

                        fragmentsRead = subscriptions[t]->poll(handler, FRAGMENTS_LIMIT);

                        if (fragmentsRead == 0) {
                            if (!reachedEos && subscriptions[t]->pollEndOfStreams(printEndOfStream) > 0) {
                                reachedEos = true;
                            }
                        }

                        pollIdleStrategy.idle(fragmentsRead);
                    }

//                    std::cout << "done polling." << std::endl;
                });

                AERON_DECL_ALIGNED(buffer_t buffer, 16);
                concurrent::AtomicBuffer srcBuffer(&buffer[0], buffer.size());


                for (int i = 0; i < settings.numberOfMessages && isRunning(); i++) {
//                    std::cout << "PUSH " << streamId << " (" << i+1 << "/" << settings.numberOfMessages << ") "
//                        << msgArray[i] << std::endl;
//                    std::cout.flush();

                    srcBuffer.putBytes(0, reinterpret_cast<std::uint8_t *>(msgArray[i]), settings.messageLength);


                    const std::int64_t result = publication->offer(srcBuffer, 0, settings.messageLength);

//                    if (result < 0) {
//                        if (BACK_PRESSURED == result) {
//                            // msg are being published faster than read
//                            std::cout << "Offer failed due to back pressure" << std::endl;
//
//                        } else if (ADMIN_ACTION == result) {
//                            // usually a log rotation with insignificant impact on performance
//                            std::cout << "Offer failed because of an administration action in the system" << std::endl;
//
//                        } else if (NOT_CONNECTED == result) {
//                            std::cout << "Offer failed because publisher is not connected to subscriber" << std::endl;
//                                running = false;
//
//                        } else if (PUBLICATION_CLOSED == result) {
//                            std::cout << "Offer failed publication is closed" << std::endl;
//                                running = false;
//
//                        } else {
//                            std::cout << "Offer failed due to unknown reason" << result << std::endl;
//                                running = false;
//                        }
//                    }

                    if (!publication->isConnected()) {
                        std::cout << "No active subscribers detected." << std::endl;
                        running = false;
                    }

                    std::this_thread::sleep_for(std::chrono::milliseconds(1));
                }

//                std::cout << "done sending." << std::endl;
                running = false;
                pollThread.join();
            }));
        }

        for (int t = 0; t < settings.processes; t++) {
            workers[t].join();
        }

//        float elapsed = float( clock () - begin_time ) /  CLOCKS_PER_SEC;
        clock_gettime(CLOCK_MONOTONIC, &finish);
        running = false;


        double elapsed = (finish.tv_sec - start.tv_sec);
        elapsed += (finish.tv_nsec - start.tv_nsec) / 1000000000.0;

        std::cout << std::fixed << std::setprecision(6);
        std::cout << elapsed << std::endl;


    } catch (const CommandOptionException& e) {
        std::cerr << std::endl << "ERROR: " << e.what() << std::endl << std::endl;
        cp.displayOptionsHelp(std::cerr);
        return -1;

    } catch (const SourcedException& e) {
        std::cerr << std::endl << "FAILED: " << e.what() << " : " << e.where() << std::endl;
        return -1;

    } catch (const std::exception& e) {
        std::cerr << std::endl << "FAILED: " << e.what() << " : " << std::endl;
        return -1;
    }


    return 0;
}
