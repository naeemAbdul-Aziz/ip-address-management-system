'use client';

import React, { useEffect, useState } from 'react';
import { 
  getNamespaces, createNamespace, 
  getSubnets, createSubnet, 
  Namespace, Subnet 
} from '../lib/api';
import SubnetGrid from '../components/SubnetGrid';
import { 
  Plus, Layers, Network, Server, 
  Activity, ShieldCheck, Search, Wand2, MapPin, Hash
} from 'lucide-react';

export default function Dashboard() {
  const [namespaces, setNamespaces] = useState<Namespace[]>([]);
  const [selectedNs, setSelectedNs] = useState<number | null>(null);
  const [subnets, setSubnets] = useState<Subnet[]>([]);
  
  // Forms
  const [newNsName, setNewNsName] = useState('');
  
  // Subnet Form
  const [newSubnetCidr, setNewSubnetCidr] = useState('');
  const [newSubnetLabel, setNewSubnetLabel] = useState('');
  const [newVlanId, setNewVlanId] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [selectedPrefix, setSelectedPrefix] = useState(24);
  
  const refreshNamespaces = async () => {
    try {
      const data = await getNamespaces();
      setNamespaces(data);
      if (data.length > 0 && !selectedNs) {
        setSelectedNs(data[0].id);
      }
    } catch (e) { console.error(e); }
  };

  const refreshSubnets = async () => {
    if (!selectedNs) return;
    try {
      const data = await getSubnets(selectedNs);
      setSubnets(data);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    refreshNamespaces();
  }, []);

  useEffect(() => {
    refreshSubnets();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedNs]);

  const handleCreateNs = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNsName) return;
    await createNamespace(newNsName);
    setNewNsName('');
    refreshNamespaces();
  };

  const handleCreateSubnet = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedNs || !newSubnetCidr || !newSubnetLabel) return;
    try {
      await createSubnet(
        selectedNs, 
        newSubnetCidr, 
        newSubnetLabel, 
        newVlanId ? parseInt(newVlanId) : undefined, 
        newLocation
      );
      setNewSubnetCidr('');
      setNewSubnetLabel('');
      setNewVlanId('');
      setNewLocation('');
      refreshSubnets();
    } catch (err: any) {
      alert('Error creating subnet: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleSuggestCidr = async () => {
    if (!selectedNs) return;
    try {
        const { getSuggestedCidr } = await import('../lib/api'); 
        const data = await getSuggestedCidr(selectedNs, selectedPrefix);
        setNewSubnetCidr(data.cidr);
    } catch (err) {
        console.error(err);
        alert('Could not find a free subnet in this scope.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans selection:bg-gray-200">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-black text-white p-1.5 rounded-lg">
              <Network size={20} />
            </div>
            <h1 className="text-lg font-semibold tracking-tight text-gray-900">
              IPAM Core
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-md text-sm text-gray-500">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              System Operational
            </div>
          </div>
        </div>
      </header>

      <main className="p-8 max-w-7xl mx-auto space-y-8">
        {/* Namespace Section */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <Layers size={14} /> Namespaces
            </h2>
            <form onSubmit={handleCreateNs} className="flex gap-2">
              <div className="relative group">
                <input 
                  value={newNsName}
                  onChange={e => setNewNsName(e.target.value)}
                  placeholder="New Namespace..." 
                  className="pl-8 pr-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 transition-all w-48 shadow-sm"
                />
                <Plus size={14} className="absolute left-2.5 top-2 text-gray-400" />
              </div>
            </form>
          </div>
          
          <div className="flex gap-3 overflow-x-auto pb-2">
            {namespaces.length === 0 && <span className="text-gray-400 text-sm italic">Create a namespace to begin...</span>}
            {namespaces.map(ns => (
              <button
                key={ns.id}
                onClick={() => setSelectedNs(ns.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all duration-200 ${
                  selectedNs === ns.id 
                    ? 'bg-black border-black text-white shadow-lg shadow-gray-200 scale-[1.02]' 
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <Server size={14} className={selectedNs === ns.id ? 'text-gray-300' : 'text-gray-400'} />
                {ns.name}
              </button>
            ))}
          </div>
        </section>

        {/* Subnets Section */}
        {selectedNs && (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
             <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-6 gap-4">
                <div className="flex items-center gap-2">
                  <h2 className="text-2xl font-semibold tracking-tight text-gray-900">Subnets</h2>
                  <span className="px-2.5 py-0.5 bg-gray-100 border border-gray-200 rounded-full text-xs font-medium text-gray-600">
                    {subnets.length} Active
                  </span>
                </div>
                
                <form onSubmit={handleCreateSubnet} className="flex flex-wrap gap-3 p-2 bg-white border border-gray-200 rounded-xl shadow-sm items-center">
                  
                  {/* Size Selector */}
                  <div className="flex items-center gap-2 px-2 border-r border-gray-100">
                    <span className="text-xs font-mono text-gray-400">PREFIX</span>
                    <select 
                        value={selectedPrefix}
                        onChange={e => setSelectedPrefix(parseInt(e.target.value))}
                        className="bg-transparent text-sm font-medium focus:outline-none cursor-pointer"
                    >
                        <option value={24}>/24 (254 IPs)</option>
                        <option value={25}>/25 (126 IPs)</option>
                        <option value={26}>/26 (62 IPs)</option>
                        <option value={27}>/27 (30 IPs)</option>
                        <option value={28}>/28 (14 IPs)</option>
                    </select>
                  </div>

                  {/* CIDR Input + Wand */}
                  <div className="relative flex items-center group">
                    <input 
                        value={newSubnetCidr}
                        onChange={e => setNewSubnetCidr(e.target.value)}
                        placeholder="CIDR..." 
                        className="pl-3 pr-8 py-1.5 bg-gray-50 rounded-lg text-sm focus:outline-none w-32 font-mono text-gray-600 border border-transparent focus:border-gray-300 transition-all"
                    />
                    <button 
                        type="button"
                        onClick={handleSuggestCidr}
                        className="absolute right-2 p-1 text-gray-400 hover:text-purple-600 transition-colors"
                        title="Auto-Suggest Next Free Subnet"
                    >
                        <Wand2 size={12} />
                    </button>
                  </div>

                  {/* Metadata Inputs */}
                  <input 
                    value={newVlanId}
                    onChange={e => setNewVlanId(e.target.value)}
                    placeholder="VLAN ID" 
                    type="number"
                    className="px-3 py-1.5 bg-transparent text-sm focus:outline-none w-20 border-l border-gray-100 text-gray-600"
                  />
                   <input 
                    value={newLocation}
                    onChange={e => setNewLocation(e.target.value)}
                    placeholder="Location (e.g. HQ)" 
                    className="px-3 py-1.5 bg-transparent text-sm focus:outline-none w-32 border-l border-gray-100 text-gray-600"
                  />
                  <div className="w-px bg-gray-200 h-6" />
                  
                  <input 
                    value={newSubnetLabel}
                    onChange={e => setNewSubnetLabel(e.target.value)}
                    placeholder="Label..." 
                    className="px-3 py-1.5 bg-transparent text-sm focus:outline-none w-32 text-gray-600 font-medium"
                  />
                  
                  <button className="bg-black text-white px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-gray-800 transition-colors flex items-center gap-2 shadow-lg shadow-gray-200">
                    <Plus size={14} /> Create
                  </button>
                </form>
             </div>

             <div className="grid grid-cols-1 gap-6">
               {subnets.map(subnet => (
                 <div key={subnet.id} className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm hover:shadow-md transition-all duration-300 group">
                    <div className="flex justify-between items-start mb-6">
                      <div className="space-y-3">
                        <div className="flex items-center gap-3">
                          <h3 className="text-xl font-mono text-gray-900 font-medium tracking-tight group-hover:text-blue-600 transition-colors">{subnet.cidr}</h3>
                          <span className="px-2.5 py-0.5 bg-gray-100 border border-gray-200 rounded-md text-xs font-semibold text-gray-600 flex items-center gap-1 uppercase tracking-wide">
                            {subnet.label}
                          </span>
                        </div>
                        
                        <div className="flex items-center gap-4 text-xs text-gray-500 font-medium">
                            {subnet.vlan_id && (
                                <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded border border-gray-100">
                                    <Hash size={12} className="text-gray-400" /> VLAN {subnet.vlan_id}
                                </span>
                            )}
                            {subnet.location && (
                                <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded border border-gray-100">
                                    <MapPin size={12} className="text-gray-400" /> {subnet.location}
                                </span>
                            )}
                             <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded border border-gray-100">
                               <ShieldCheck size={12} className="text-emerald-500" /> Strict
                            </span>
                        </div>
                      </div>
                      
                      <div className="text-right">
                        <div className="text-2xl font-bold text-gray-900">{subnet.utilization?.toFixed(1)}%</div>
                        <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">Utilization</div>
                      </div>
                    </div>
                    
                    {/* Utilization Bar */}
                    <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden mb-8">
                      <div 
                        className={`h-full transition-all duration-1000 ease-out rounded-full ${
                          (subnet.utilization || 0) > 90 ? 'bg-red-500' : 'bg-black'
                        }`} 
                        style={{ width: `${subnet.utilization}%` }}
                      />
                    </div>
                    
                    <SubnetGrid subnet={subnet} />
                 </div>
               ))}
               
               {subnets.length === 0 && (
                 <div className="flex flex-col items-center justify-center py-24 bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200">
                   <div className="bg-white p-4 rounded-full shadow-sm mb-4">
                     <Search size={32} className="text-gray-300" />
                   </div>
                   <h3 className="text-lg font-medium text-gray-900">No Subnets Found</h3>
                   <p className="text-gray-500 text-sm mt-1 max-w-sm text-center">
                     Use the creation bar above to add your first subnet. Try the <strong>Magic Wand</strong> for auto-suggestions!
                   </p>
                 </div>
               )}
             </div>
          </section>
        )}
      </main>
    </div>
  );
}
