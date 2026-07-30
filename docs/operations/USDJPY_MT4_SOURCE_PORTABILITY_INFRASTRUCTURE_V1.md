# MT4 Source Portability Infrastructure

HST, terminal chart history, generated FXT, tester history, and Model=0 are not broker-native raw Tick authority. Common same-timestamp order is market update → indicator update → exit check → close → realized-state update → lifecycle release → signal evaluation → suppression → entry → portfolio snapshot.
