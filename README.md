Basic architecture

Load Balancer is a flask server with a reverse proxy and a round robin algorithm to select the server.

HeartBeat server is a flask server which does health checking periodically.
It holds the state data for the cluster.
So, this is the center of the cluster.

Auto-scaler is another flask server. This gets the data from the HeartBeat server and, if needed, starts another server or stops an existing server.
