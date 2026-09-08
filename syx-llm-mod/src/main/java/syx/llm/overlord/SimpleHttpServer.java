package syx.llm.overlord;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Minimal HTTP/1.1 server using only java.base (game JRE has no jdk.httpserver).
 */
final class SimpleHttpServer {

    interface Handler {
        void handle(Request request, Response response) throws IOException;
    }

    static final class Request {
        final String method;
        final String path;
        final String body;

        Request(String method, String path, String body) {
            this.method = method;
            this.path = path;
            this.body = body;
        }
    }

    static final class Response {
        int status = 200;
        String contentType = "application/json";
        String body = "";

        void json(int status, String json) {
            this.status = status;
            this.contentType = "application/json";
            this.body = json;
        }
    }

    private final int port;
    private final ExecutorService workers;
    private final AtomicBoolean running = new AtomicBoolean(false);
    private ServerSocket serverSocket;
    private Thread acceptThread;

    SimpleHttpServer(int port, int workerThreads) {
        this.port = port;
        this.workers = Executors.newFixedThreadPool(workerThreads);
    }

    void route(String path, Handler handler) {
        routes.put(path, handler);
    }

    private final java.util.Map<String, Handler> routes = new java.util.HashMap<>();

    void start() throws IOException {
        if (!running.compareAndSet(false, true)) {
            return;
        }
        serverSocket = new ServerSocket();
        serverSocket.bind(new InetSocketAddress("127.0.0.1", port));
        acceptThread = new Thread(this::acceptLoop, "llm-overlord-http");
        acceptThread.setDaemon(true);
        acceptThread.start();
    }

    void stop() {
        running.set(false);
        try {
            if (serverSocket != null) {
                serverSocket.close();
            }
        } catch (IOException ignored) {
        }
        workers.shutdownNow();
    }

    private void acceptLoop() {
        while (running.get()) {
            try {
                Socket client = serverSocket.accept();
                workers.execute(() -> handleClient(client));
            } catch (IOException e) {
                if (running.get()) {
                    System.err.println("[LLM Overlord] HTTP accept error: " + e.getMessage());
                }
            }
        }
    }

    private void handleClient(Socket client) {
        try (client;
             BufferedReader in = new BufferedReader(
                     new InputStreamReader(client.getInputStream(), StandardCharsets.UTF_8));
             OutputStream out = client.getOutputStream()) {

            String requestLine = in.readLine();
            if (requestLine == null || requestLine.isBlank()) {
                return;
            }

            String[] parts = requestLine.split(" ");
            if (parts.length < 2) {
                return;
            }
            String method = parts[0];
            String path = parts[1].split("\\?")[0];

            int contentLength = 0;
            String line;
            while ((line = in.readLine()) != null && !line.isEmpty()) {
                int idx = line.indexOf(':');
                if (idx <= 0) {
                    continue;
                }
                String name = line.substring(0, idx).trim().toLowerCase();
                String value = line.substring(idx + 1).trim();
                if ("content-length".equals(name)) {
                    contentLength = Integer.parseInt(value);
                }
            }

            String body = "";
            if (contentLength > 0) {
                char[] buf = new char[contentLength];
                int read = 0;
                while (read < contentLength) {
                    int n = in.read(buf, read, contentLength - read);
                    if (n < 0) {
                        break;
                    }
                    read += n;
                }
                body = new String(buf, 0, read);
            }

            Handler handler = routes.get(path);
            Response response = new Response();
            if (handler == null) {
                response.json(404, "{\"error\":\"Not found\"}");
            } else {
                handler.handle(new Request(method, path, body), response);
            }

            byte[] bytes = response.body.getBytes(StandardCharsets.UTF_8);
            String statusText = response.status == 200 ? "OK"
                    : response.status == 400 ? "Bad Request"
                    : response.status == 405 ? "Method Not Allowed"
                    : response.status == 503 ? "Service Unavailable"
                    : "Error";
            String headers =
                    "HTTP/1.1 " + response.status + " " + statusText + "\r\n"
                    + "Content-Type: " + response.contentType + "\r\n"
                    + "Content-Length: " + bytes.length + "\r\n"
                    + "Access-Control-Allow-Origin: *\r\n"
                    + "Connection: close\r\n\r\n";
            out.write(headers.getBytes(StandardCharsets.UTF_8));
            out.write(bytes);
            out.flush();
        } catch (Exception e) {
            System.err.println("[LLM Overlord] HTTP client error: " + e.getMessage());
        }
    }
}
