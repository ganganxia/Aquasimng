/*
 * aloha_tests.cc
 *
 *  Created on: March 8, 2019
 *      Author: dmitry
 */


#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/aqua-sim-ng-module.h"
#include "ns3/aqua-sim-propagation.h"
#include "ns3/applications-module.h"
#include "ns3/log.h"
#include "ns3/callback.h"

#include <random>
#include <math.h>
#include <iomanip>
#include <sstream>
#include <chrono>

/*
 * ALOHA NxN grid random destination topology tests
 *
 *
 */

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("ALOHA_grid_test");


int
main (int argc, char *argv[])
{
  double simStop = 100; //seconds
//  double simStop = 2; //seconds

  int n_nodes = 4;
//  int sinks = 1;
//  uint32_t m_dataRate = 80000; // bps
  double m_dataRate = 80000; // bps

  double m_packetSize = 88; // bytes
  double range = 1000000.0;	// meters, set to -1 to disable distance-based reception

  // Poisson traffic parameters
  double lambda = 0.02;

  // Grid parameters
  int max_x = 100; // meters
//  int max_y = 10000; // meters
//  double distance = 10; // meters

  // Max Tx power
  double max_tx_power = 30; // Watts

//  LogComponentEnable ("ASBroadcastMac", LOG_LEVEL_INFO);

  //to change on the fly
  CommandLine cmd;
  cmd.AddValue ("simStop", "Length of simulation", simStop);
  cmd.AddValue ("lambda", "Packet arrival rate", lambda);
  cmd.AddValue ("packet_size", "Packet size", m_packetSize);
  cmd.AddValue ("grid_size", "Grid size, in km", max_x);
  cmd.AddValue ("n_nodes", "Number of nodes", n_nodes);
  cmd.AddValue ("range", "Transmission range", range);
  cmd.AddValue ("tx_power", "Max transmission power", max_tx_power);


  cmd.Parse(argc,argv);

  // Random integer selection-related parameters
  std::random_device rd;     // only used once to initialise (seed) engine
  std::mt19937 rng(rd());    // random-number engine used (Mersenne-Twister in this case)
  std::uniform_int_distribution<int> uni_distance(0, max_x); // guaranteed unbiased
  std::uniform_int_distribution<int> uni_nodes(0, n_nodes - 1); // guaranteed unbiased

  //std::cout <<m_packetSize<< std::endl;
  std::cout << "-----------Initializing simulation-----------\n";
  auto start = std::chrono::high_resolution_clock::now();

  NodeContainer nodesCon;
//  NodeContainer sinksCon;
  nodesCon.Create(n_nodes);
//  sinksCon.Create(sinks);

  PacketSocketHelper socketHelper;
  socketHelper.Install(nodesCon);
//  socketHelper.Install(sinksCon);

  //establish layers using helper's pre-build settings
  AquaSimChannelHelper channel = AquaSimChannelHelper::Default();
  channel.SetPropagation("ns3::AquaSimSimplePropagation");
  AquaSimHelper asHelper = AquaSimHelper::Default();
  asHelper.SetChannel(channel.Create());

  asHelper.SetMac("ns3::AquaSimAloha", "AckOn", IntegerValue(1), "MinBackoff", DoubleValue(0.0),
		  "MaxBackoff", DoubleValue(1.5));
  asHelper.SetEnergyModel(
      "ns3::AquaSimEnergyModel",
      "InitialEnergy", DoubleValue(1e12),   // 初始能量极大，相当于无限电
      "TxPower", DoubleValue(0.0),          // 发射时不耗电
      "RxPower", DoubleValue(0.0)           // 接收时不耗电
  );
  asHelper.SetRouting("ns3::AquaSimRoutingDummy");

  // Define the Tx power
  asHelper.SetPhy("ns3::AquaSimPhyCmn", "PT", DoubleValue(max_tx_power));
  /*asHelper.SetPhy("ns3::AquaSimPhyCmn", 
    "PT", DoubleValue(max_tx_power),
    "Preamble", TimeValue(Seconds(0)),      // 强制前导码时间为0
    "CPHeader", TimeValue(Seconds(0))       // 强制控制包头时间为0
);*/
  /*
   * Set up mobility model for nodes and sinks
   */
  MobilityHelper mobility;
  NetDeviceContainer devices;
  Ptr<ListPositionAllocator> position = CreateObject<ListPositionAllocator> ();
  Vector boundry = Vector(0,0,0);

  std::cout << "Creating Nodes\n";

  // Grid layout logic
  int nodes_per_row = static_cast<int>(sqrt(n_nodes));
  double node_spacing = 100.0; // meters, as in the python script
  int node_index = 0;

  for (NodeContainer::Iterator i = nodesCon.Begin(); i != nodesCon.End(); ++i, ++node_index)
    {
      Ptr<AquaSimNetDevice> newDevice = CreateObject<AquaSimNetDevice>();

      // Calculate grid position
      int row = node_index / nodes_per_row;
      int col = node_index % nodes_per_row;
      boundry.x = col * node_spacing;
      boundry.y = row * node_spacing;

      position->Add(boundry);
      devices.Add(asHelper.Create(*i, newDevice));

      //      NS_LOG_DEBUG("Node:" << newDevice->GetAddress() << " position(x):" << boundry.x);
      //      std::cout << "Node:" << newDevice->GetAddress() << " position(x):" << boundry.x <<
      //    		  " position(y):" << boundry.y << "\n";
      newDevice->GetPhy()->SetTransRange(range);
      //      newDevice->GetPhy()->SetTxPower(0.001);
    }

  mobility.SetPositionAllocator(position);
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(nodesCon);
//  mobility.Install(sinksCon);

  int j = 0;
  char duration_on[300];
  char duration_off[300];

  // Set application to each node
  for (NodeContainer::Iterator i = nodesCon.Begin(); i != nodesCon.End(); i++)
  {
	  AquaSimApplicationHelper app ("ns3::PacketSocketFactory", n_nodes);

	  //sprintf(duration_on, "ns3::ConstantRandomVariable[Constant=%f]", 0.01);
    sprintf(duration_on, "ns3::ExponentialRandomVariable[Mean=%f]",(m_packetSize * 8) / m_dataRate);
	  sprintf(duration_off, "ns3::ExponentialRandomVariable[Mean=%f]",1.0 / lambda);
//	  std::cout << "Duration On: " << duration_on << "\n";
//	  std::cout << "Duration Off: " << duration_off << "\n";
	  app.SetAttribute ("OnTime", StringValue (duration_on));
	  app.SetAttribute ("OffTime", StringValue (duration_off));

	  app.SetAttribute ("DataRate", DataRateValue (m_dataRate));
	  app.SetAttribute ("PacketSize", UintegerValue (m_packetSize));

	  ApplicationContainer apps = app.Install (nodesCon.Get(j));

	  apps.Start (Seconds (0.5));
	  apps.Stop (Seconds (simStop + 1));

	  j++;
  }
  Simulator::Schedule(Seconds(simStop - 0.0001), [](){
    std::cout << "Simulation reached scheduled stop time: "
              << Simulator::Now().GetSeconds() << " s\n";
  });
  Packet::EnablePrinting (); //for debugging purposes
  std::cout << "-----------Running Simulation-----------\n";
  Simulator::Stop(Seconds(simStop));

  // Enable ASCII trace files
  Packet::EnablePrinting ();  //for debugging purposes
  char buff[1000];
  // Naming convention: lambda-number_of_nodes-n_intermediate_nodes-seed
  std::stringstream stream;
  stream << std::fixed << std::setprecision(4) << lambda;
  std::string lambda_string = stream.str();
  snprintf(buff, sizeof(buff), "aloha-density-trace-%s-%d-%d.asc", lambda_string.c_str(), n_nodes, 0);
  std::string asciiTraceFile = buff;

  // std::string asciiTraceFile = "aloha-trace.asc";
  // asciiTraceFile.
  std::ofstream ascii (asciiTraceFile.c_str());
  if (!ascii.is_open()) {
    NS_FATAL_ERROR("Could not open trace file.");
  }
  asHelper.EnableAsciiAll(ascii);

  Simulator::Run();
  for (int i = 0; i < n_nodes; ++i) {
    Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice>(devices.Get(i));
    if (dev && dev->EnergyModel()) {
        std::cout << "Node " << i
                  << " Remaining Energy: "
                  << dev->EnergyModel()->GetEnergy() << " J\n";
    }
}
  auto end = std::chrono::high_resolution_clock::now();
  std::chrono::duration<double> elapsed = end - start;
  std::cout << "Total simulation time: " << elapsed.count() << " seconds\n";
  asHelper.GetChannel()->PrintCounters();

  Simulator::Destroy();

  std::cout << "fin.\n";
  return 0;
}
