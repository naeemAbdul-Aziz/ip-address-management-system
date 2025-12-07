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
  Activity, ShieldCheck, Search, Wand2, MapPin, Hash, Sparkles, ArrowRight
} from 'lucide-react';

export default function Dashboard() {
  const [namespaces, setNamespaces] = useState<Namespace[]>([]);
  const [selectedNs, setSelectedNs] = useState<number | null>(null);
  const [subnets, setSubnets] = useState<Subnet[]>([]);
  
  // Forms
  const [newNsName, setNewNsName] = useState('');
  const [newNsCidr, setNewNsCidr] = useState('');
  
  const CIDR_PRESETS = [
    { label: 'Large (10.x.x.x)', value: '10.0.0.0/8' },
    { label: 'Medium (172.16.x.x)', value: '172.16.0.0/12' },
    { label: 'Small (192.168.x.x)', value: '192.168.0.0/16' },
    { label: 'Custom', value: 'custom' },
  ];
  const [selectedPreset, setSelectedPreset] = useState(CIDR_PRESETS[0].value);

  // Subnet Form
  const [newSubnetCidr, setNewSubnetCidr] = useState('');
  const [newSubnetLabel, setNewSubnetLabel] = useState('');
  const [newVlanId, setNewVlanId] = useState('');
  const [newLocation, setNewLocation] = useState('');
  const [selectedPrefix, setSelectedPrefix] = useState(24);
  const [isSuggesting, setIsSuggesting] = useState(false);
  
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
  
  // Sync preset to cidr
  useEffect(() => {
    if (selectedPreset !== 'custom') {
        setNewNsCidr(selectedPreset);
    }
  }, [selectedPreset]);

  const handleCreateNs = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNsName) return;
    try {
      // Default to 10.0.0.0/8 if empty for backward compat/laziness, but let backend validate
      await createNamespace(newNsName, newNsCidr || '10.0.0.0/8');
      setNewNsName('');
      setNewNsCidr(CIDR_PRESETS[0].value);
      setSelectedPreset(CIDR_PRESETS[0].value);
      refreshNamespaces();
    } catch (error: any) {
      console.error("Failed to create namespace:", error);
      alert('Failed to create namespace: ' + (error.response?.data?.detail || error.message));
    }
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
    setIsSuggesting(true);
    try {
        const { getSuggestedCidr } = await import('../lib/api'); 
        const data = await getSuggestedCidr(selectedNs, selectedPrefix);
        setNewSubnetCidr(data.cidr);
    } catch (err) {
        console.error(err);
        alert('Could not find a free subnet in this scope.');
    } finally {
        setIsSuggesting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 font-sans selection:bg-gray-200 pb-20">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white/80 backdrop-blur-md sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 md:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-black text-white p-1.5 rounded-lg shadow-sm">
              <Network size={20} />
            </div>
            <h1 className="text-lg font-semibold tracking-tight text-gray-900 hidden md:block">
              IPAM Core
            </h1>
            <h1 className="text-lg font-semibold tracking-tight text-gray-900 md:hidden">
              IPAM
            </h1>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 rounded-full text-xs font-medium text-emerald-700 border border-emerald-100">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Operational
            </div>
          </div>
        </div>
      </header>

      <main className="p-4 md:p-8 max-w-7xl mx-auto space-y-8">
        {/* Namespace Section */}
        <section className="space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <Layers size={14} /> Namespaces (Environments)
            </h2>
            <form onSubmit={handleCreateNs} className="w-full md:w-auto">
              <div className="relative group flex items-center gap-2">
                <div className="relative flex-1">
                    <input 
                    value={newNsName}
                    onChange={e => setNewNsName(e.target.value)}
                    placeholder="Name (e.g. Prod)" 
                    className="w-full md:w-48 pl-9 pr-3 py-2 bg-white border border-gray-200 rounded-lg text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 transition-all shadow-sm"
                    />
                    <Plus size={16} className="absolute left-3 top-2.5 text-gray-400 group-focus-within:text-black transition-colors" />
                </div>
                
                <div className="relative w-40 md:w-48">
                    {selectedPreset === 'custom' ? (
                         <input 
                         value={newNsCidr}
                         onChange={e => setNewNsCidr(e.target.value)}
                         placeholder="Root CIDR" 
                         autoFocus
                         className="w-full pl-3 pr-9 py-2 bg-white border border-gray-200 rounded-lg text-base focus:outline-none focus:ring-2 focus:ring-gray-200 transition-all shadow-sm font-mono"
                         />
                    ) : (
                        <select
                            value={selectedPreset}
                            onChange={e => setSelectedPreset(e.target.value)}
                            className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-gray-200 transition-all shadow-sm text-gray-600 appearance-none cursor-pointer"
                        >
                            {CIDR_PRESETS.map(p => (
                                <option key={p.value} value={p.value} className="text-gray-900">{p.label}</option>
                            ))}
                        </select>
                    )}
                    
                     {selectedPreset === 'custom' && (
                        <button 
                            type="button" 
                            onClick={() => setSelectedPreset(CIDR_PRESETS[0].value)}
                            className="absolute right-9 top-1 bottom-1 p-1 text-gray-400 hover:text-black"
                            title="Back to Presets"
                        >
                            <span className="text-[10px] font-bold">X</span>
                        </button>
                     )}

                     <button 
                        type="submit" 
                        className="absolute right-1 top-1 bottom-1 p-1.5 text-black bg-gray-100 hover:bg-black hover:text-white rounded-md transition-all shadow-sm"
                        title="Create Namespace"
                        >
                        <ArrowRight size={14} />
                    </button>
                </div>
              </div>
            </form>
          </div>
          
          <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide -mx-4 px-4 md:mx-0 md:px-0">
            {namespaces.length === 0 && (
                <div className="text-center w-full py-8 border-2 border-dashed border-gray-200 rounded-xl bg-white/50">
                    <p className="text-gray-500 text-sm">No environments found. Create one above!</p>
                </div>
            )}
            {namespaces.map(ns => (
              <button
                key={ns.id}
                onClick={() => setSelectedNs(ns.id)}
                className={`flex-shrink-0 flex flex-col items-start gap-1 px-5 py-3 rounded-xl border text-sm font-medium transition-all duration-200 min-w-[140px] ${
                  selectedNs === ns.id 
                    ? 'bg-black border-black text-white shadow-lg shadow-gray-200 scale-[1.02]' 
                    : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center gap-2 w-full">
                    <Server size={16} className={selectedNs === ns.id ? 'text-gray-300' : 'text-gray-400'} />
                    <span>{ns.name}</span>
                </div>
                {ns.cidr && (
                    <span className={`text-[10px] font-mono pl-6 ${selectedNs === ns.id ? 'text-gray-400' : 'text-gray-400'}`}>
                        {ns.cidr}
                    </span>
                )}
              </button>
            ))}
          </div>
        </section>

        {/* Subnets Section */}
        {selectedNs && (
          <section className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
             <div className="bg-white rounded-2xl p-4 md:p-6 shadow-sm border border-gray-100">
                <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-2">
                    <div>
                        <h2 className="text-xl font-semibold tracking-tight text-gray-900">Network Blocks</h2>
                        <p className="text-sm text-gray-500">Manage IP ranges for this environment.</p>
                    </div>
                     <span className="self-start md:self-center px-3 py-1 bg-gray-100 border border-gray-200 rounded-full text-xs font-medium text-gray-600">
                        {subnets.length} Active Subnets
                    </span>
                </div>
                
                {/* Creation Form - Responsive Grid */}
                <form onSubmit={handleCreateSubnet} className="grid grid-cols-1 md:grid-cols-12 gap-3">
                  
                  {/* Size Selector */}
                  <div className="md:col-span-2 relative bg-gray-50 rounded-lg border border-gray-200 px-3 py-2">
                    <span className="absolute top-1 left-3 text-[10px] font-bold text-gray-400 uppercase tracking-wider">Size</span>
                    <select 
                        value={selectedPrefix}
                        onChange={e => setSelectedPrefix(parseInt(e.target.value))}
                        className="w-full bg-transparent text-base md:text-sm font-medium focus:outline-none cursor-pointer mt-3 pt-0.5"
                    >
                        <option value={24}>/24 (Large)</option>
                        <option value={25}>/25 (Half)</option>
                        <option value={26}>/26 (Medium)</option>
                        <option value={27}>/27 (Small)</option>
                        <option value={28}>/28 (Tiny)</option>
                    </select>
                  </div>

                  {/* CIDR Input + Wand */}
                  <div className="md:col-span-3 relative group">
                    <input 
                        value={newSubnetCidr}
                        onChange={e => setNewSubnetCidr(e.target.value)}
                        placeholder="Network CIDR..." 
                        className="w-full h-full pl-3 pr-10 py-3 bg-white border border-gray-200 rounded-lg text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-black/5 font-mono text-gray-700 transition-all"
                    />
                    <button 
                        type="button"
                        onClick={handleSuggestCidr}
                        disabled={isSuggesting}
                        className="absolute right-2 top-2 bottom-2 p-1.5 text-gray-400 hover:text-purple-600 hover:bg-purple-50 rounded-md transition-colors disabled:animate-spin"
                        title="Auto-Suggest Next Free Subnet"
                    >
                        <Wand2 size={16} />
                    </button>
                  </div>

                  {/* Vlan & Location - Stacked on mobile, side-by-side on desktop */}
                  <input 
                    value={newVlanId}
                    onChange={e => setNewVlanId(e.target.value)}
                    placeholder="VLAN ID (Opt)" 
                    type="number"
                    className="md:col-span-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-black/5"
                  />
                   <input 
                    value={newLocation}
                    onChange={e => setNewLocation(e.target.value)}
                    placeholder="Location (Opt)" 
                    className="md:col-span-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-black/5"
                  />
                  
                  <input 
                    value={newSubnetLabel}
                    onChange={e => setNewSubnetLabel(e.target.value)}
                    placeholder="Label (e.g. Web Servers)..." 
                    className="md:col-span-2 px-3 py-2 bg-white border border-gray-200 rounded-lg text-base md:text-sm focus:outline-none focus:ring-2 focus:ring-black/5 font-medium"
                  />
                  
                  <button className="md:col-span-1 bg-black text-white rounded-lg text-sm font-bold hover:bg-gray-800 transition-colors flex items-center justify-center gap-2 shadow-lg shadow-gray-200 active:scale-95 py-3 md:py-0">
                    <Plus size={16} /> <span className="md:hidden">Create Block</span>
                  </button>
                </form>
             </div>

             <div className="grid grid-cols-1 gap-6">
               {subnets.map(subnet => (
                 <div key={subnet.id} className="bg-white border border-gray-200 rounded-2xl p-5 md:p-6 shadow-sm hover:shadow-md transition-all duration-300 group">
                    <div className="flex flex-col md:flex-row justify-between items-start mb-6 gap-4">
                      <div className="space-y-3 w-full md:w-auto">
                        <div className="flex items-center gap-3 flex-wrap">
                          <h3 className="text-xl font-mono text-gray-900 font-medium tracking-tight group-hover:text-blue-600 transition-colors">{subnet.cidr}</h3>
                          <span className="px-2.5 py-0.5 bg-gray-100 border border-gray-200 rounded-md text-xs font-semibold text-gray-600 flex items-center gap-1 uppercase tracking-wide">
                            {subnet.label}
                          </span>
                        </div>
                        
                        <div className="flex items-center gap-3 text-xs text-gray-500 font-medium flex-wrap">
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
                               <ShieldCheck size={12} className="text-emerald-500" /> Protected
                            </span>
                        </div>
                      </div>
                      
                      <div className="flex items-center md:flex-col md:items-end gap-3 md:gap-0 w-full md:w-auto justify-between md:justify-start pt-2 md:pt-0 border-t md:border-t-0 border-gray-100">
                        <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">Utilization</div>
                        <div className="text-2xl font-bold text-gray-900">{subnet.utilization?.toFixed(1)}%</div>
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
                 <div className="flex flex-col items-center justify-center py-12 md:py-24 bg-gray-50 rounded-2xl border-2 border-dashed border-gray-200 mx-4 md:mx-0">
                   <div className="bg-white p-4 rounded-full shadow-sm mb-4">
                     <Sparkles size={32} className="text-purple-400" />
                   </div>
                   <h3 className="text-lg font-medium text-gray-900">Your Network Canvas is Empty</h3>
                   <p className="text-gray-500 text-sm mt-2 max-w-sm text-center px-4">
                     Start by adding a subnet block above. <br/>
                     <strong>Pro Tip:</strong> Select a size (e.g., /24) and click the <Wand2 className="inline text-purple-500 w-3 h-3"/> Wand to auto-find a spot!
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
