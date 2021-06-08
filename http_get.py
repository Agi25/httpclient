import socket
import ssl
import sys
import re


def getHostnameAndSubfolder(url):
    port = 0
    host = ""
    subfolder = "/"

    if re.match("http://", url):
        host = url.replace("http://", "")
        hostsplit = host.split("/", maxsplit=1)
        port = 80
        host = hostsplit[0]
        if len(hostsplit) > 1:
            subfolder += hostsplit[1]

    elif re.match("https://", url):
        host = url.replace("https://", "")
        hostsplit = host.split("/", maxsplit=1)
        port = 443
        host = hostsplit[0]
        if len(hostsplit) > 1:
            subfolder += hostsplit[1]

    else:
        # Not specified, using standard port
        hostsplit = url.split("/", maxsplit=1)
        port = 80
        host = hostsplit[0]
        if len(hostsplit) > 1:
            subfolder += hostsplit[1]

    return host, subfolder, port


def main():
    # Improper number of input argument
    if len(sys.argv) != 2:
        sys.exit(2)
    URL = sys.argv[1]
    verbose = False
    while True:
        HOST_NAME, SUB_FOLDER, PORT_NUMBER = getHostnameAndSubfolder(URL)
        if verbose:
            print(HOST_NAME + " " + SUB_FOLDER + " " + str(PORT_NUMBER))

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if verbose:
                print("Socket created succesfully!")

        except socket.error as e:
            if verbose:
                print("Failed to create a socket")
                print("Reason : () ".format(e))
            sys.exit()
        if verbose:
            print("######### New Connection #########")
            print("URL: " + URL)
            print("Hostname: " + HOST_NAME)
            print("Subfolder: " + SUB_FOLDER)

        try:
            s.connect((HOST_NAME.strip(), PORT_NUMBER))
            if PORT_NUMBER == 443:
                s = ssl.wrap_socket(s)

            if verbose:
                print("Socket connected to host " + HOST_NAME + " on port " + str(PORT_NUMBER))

        except socket.error as e:
            print("Failed connection to host " + HOST_NAME + " on port " + str(PORT_NUMBER), file=sys.stderr)
            print("Reason ", str(e), file=sys.stderr)
            sys.exit()

        headerContainer = dict()
        length = 0

        socketFile = s.makefile(mode='rwb', encoding='utf-8')
        # Assemble message
        message = "GET %s HTTP/1.1\r\nHost:%s\r\n\r\n" % (SUB_FOLDER.strip(), HOST_NAME.strip())
        socketFile.write(message.encode())
        socketFile.flush()
        status = bytes.decode(socketFile.readline()).strip()
        headerContainer["status"] = status.strip()
        # Parse header
        while True:
            line = bytes.decode(socketFile.readline())

            if line.__contains__(":"):
                content = line.split(":", 1)
                headerContainer[content[0].strip().lower()] = content[1].strip()
            else:
                break
        # # Prints content of header
        if verbose:
            for key in headerContainer.keys():
                print(key + ": " + headerContainer[key])
        # Process status 200
        if re.search("200 OK", status):
            if verbose:
                print(status)
            # Process transfer-encoding: chunked
            if "transfer-encoding" in headerContainer.keys():
                if headerContainer["transfer-encoding"] == "chunked":
                    while True:
                        line = socketFile.readline()

                        if verbose:
                            print(len(line))
                        if bytes.decode(line):
                            try:
                                if int(bytes.decode(line), 16) == 0:
                                    if verbose:
                                        print("LAST CHUNK RECEIVED")
                                    break
                            except ValueError as e:
                                sys.stdout.buffer.write(line)
                    s.close()
                    break
            # Process content-length
            else:
                while True:
                    line = socketFile.readline()
                    length += len(line)
                    sys.stdout.buffer.write(line)
                    if verbose:
                        print(length)
                        print(length, end=" Counted bytes\n")
                        print(int(headerContainer["content-length"]), end=" Expected length\n")
                        print(length == int(headerContainer["content-length"]), end=" Is equal?\n")
                    if len(line) == 0 or length >= int(headerContainer["content-length"]):
                        break
                if verbose:
                    print("PRINT CONTENT")
                s.close()
                break
        # Process redirecting
        elif re.search("30", status):
            if verbose:
                print(status)
            headerContainer["status"] = status
            URL = headerContainer["location"].strip()
            s.close()
        # Process unimplemented behaviour
        else:
            if verbose:
                print(status)
            while True:
                line = socketFile.readline()
                length += len(line)
                sys.stderr.buffer.write(line)
                if verbose:
                    print(length)
                    print(length, end=" Counted bytes\n")
                    print(int(headerContainer["content-length"]), end=" Expected length\n")
                    print(length == int(headerContainer["content-length"]), end=" Is equal?\n")
                if len(line) == 0 or length >= int(headerContainer["content-length"]):
                    break
            sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    main()
