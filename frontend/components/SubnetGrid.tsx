import React, { useEffect, useState } from 'react';
import { Subnet, IPAddress, getSubnetIPs, allocateIP, releaseIp } from '../lib/api';
import { Plus, RefreshCw } from 'lucide-react';

interface SubnetGridProps {
  subnet: Subnet;
}

export default function SubnetGrid({ subnet }: SubnetGridProps) {
  const [ips, setIps] = useState<IPAddress[]>([]);
  const [loading, setLoading] = useState(false);
  const [allocating, setAllocating] = useState(false);

  const fetchIPs = async () => {
    try {
      setLoading(true);
      const data = await getSubnetIPs(subnet.id);
      setIps(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIPs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subnet.id]);

  const handleAllocate = async () => {
    if (allocating) return;
    
    // Simple prompt for MVP - can be replaced with Modal later
    const deviceName = prompt("Enter Device Name / Hostname (Optional):");
    if (deviceName === null) return; // Cancelled

    try {
      setAllocating(true);
      await allocateIP(subnet.id, deviceName || undefined);
      await fetchIPs(); // Refresh
    } catch (error) {
      alert('Failed to allocate IP (Subnet might be full)');
      console.error(error);
    } finally {
      setAllocating(false);
    }
  };

  const totalSlots = 256; 
  const cells = [];
  const ipMap = new Map<string, IPAddress>();
  ips.forEach(ip => ipMap.set(ip.address, ip));
  const isSlash24 = subnet.cidr.endsWith('/24');
  const baseIP = subnet.cidr.split('/')[0].split('.').slice(0, 3).join('.');

  if (isSlash24) {
    for (let i = 0; i < totalSlots; i++) {
      const currentIP = `${baseIP}.${i}`;
      const existing = ipMap.get(currentIP);
      
      // Apple-style minimalist palette
      // Free: Very subtle gray or white with border
      // Active: Solid black or specific status color
      let statusClass = "bg-gray-50 border border-gray-200 hover:border-gray-400 cursor-pointer"; // Free
      
      if (existing) {
        statusClass = "bg-black border-black cursor-not-allowed"; // Active
        if (existing.status === 'reserved') statusClass = "bg-orange-500 border-orange-500 cursor-not-allowed";
      }
      
      // Network/Broadcast
      if (i === 0 || i === 255) statusClass = "bg-gray-200 border-gray-200 cursor-not-allowed opacity-50";

      cells.push(
        <div 
          key={i} 
          title={existing ? `${currentIP} (${existing.hostname})` : currentIP}
          className={`w-3 h-3 rounded-[2px] ${statusClass} transition-all duration-200`}
          onClick={() => {
            if (!existing && i !== 0 && i !== 255) {
                handleAllocate();
            } else if (existing) {
                if (window.confirm(`Release IP ${currentIP}?`)) {
                    releaseIp(existing.id).then(fetchIPs).catch(e => alert(e.message));
                }
            }
          }}
        />
      );
    }
  } else {
    // List view fallback
    return (
      <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
        <p className="text-gray-500 text-sm mb-2">Visualizer optimized for /24.</p>
        <div className="flex flex-wrap gap-2">
            {ips.map(ip => (
                <span key={ip.id} className="bg-black text-white text-xs px-2 py-1 rounded-md font-medium">{ip.address}</span>
            ))}
        </div>
         <div className="mt-2">
              <button
               onClick={handleAllocate}
               disabled={allocating}
               className="bg-black text-white px-3 py-1.5 rounded-md text-xs font-medium hover:bg-gray-800 disabled:opacity-50"
             >
               + Allocate New
             </button>
         </div>
        </div>

    );
  }

  return (
    <div className="mt-6 bg-gray-50/50 p-6 rounded-xl border border-gray-100">
      <div className="flex justify-between items-center mb-4">
        <div className="flex gap-4 text-xs font-medium text-gray-500">
            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] border border-gray-300 bg-gray-50"></div> Available</span>
            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] bg-black"></div> Active</span>
            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] bg-orange-500"></div> Reserved</span>
        </div>
        
        <button
          onClick={handleAllocate}
          disabled={allocating}
          className="text-xs font-medium text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-1 transition-colors"
        >
          {allocating ? <RefreshCw size={12} className="animate-spin" /> : <Plus size={12} />}
          Allocate Next Available
        </button>
      </div>

      <div className="grid grid-cols-16 gap-1 w-fit mx-auto">
        {cells}
      </div>
    </div>
  );
}
