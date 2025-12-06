print("Bradley AI online.")
print("Guardian program activated.")
print("Protecting the grid…\n")

from agents.swarm import BradleySwarm

swarm = BradleySwarm()
swarm.run_real_threat_test()
