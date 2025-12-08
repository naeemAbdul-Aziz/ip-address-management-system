import React, { useEffect, useState } from 'react';
import { Subnet, IPAddress, getSubnetIPs, allocateIP, reserveIP, releaseIp } from '../lib/api';
import { Plus, RefreshCw, Shield, ShieldCheck } from 'lucide-react';

interface SubnetGridProps {
  subnet: Subnet;
}

export default function SubnetGrid({ subnet }: SubnetGridProps) {
  const [ips, setIps] = useState<IPAddress[]>([]);
  const [loading, setLoading] = useState(false);
  const [allocating, setAllocating] = useState(false);
  const [reservationMode, setReservationMode] = useState(false);

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

  const handleInteraction = async (ipAddress?: string, existingId?: number) => {
    if (allocating) return;

    // RELEASE/DELETE LOGIC
    if (existingId) {
       if (window.confirm(`Release/Delete IP ${ipAddress}?`)) {
           try {
               await releaseIp(existingId);
               fetchIPs();
           } catch (e: any) {
               alert(e.message);
           }
       }
       return;
    }

    // ALLOCATION / RESERVATION LOGIC
    setAllocating(true);
    try {
        if (reservationMode) {
             // Reserve Mode
             await reserveIP(subnet.id, ipAddress, "Reserved via Admin UI");
        } else {
             // Allocation Mode
             const deviceName = prompt("Enter Device Name / Hostname (Optional):");
             if (deviceName === null) { setAllocating(false); return; } // Cancelled
             
             await allocateIP(subnet.id, deviceName || undefined);
        }
        await fetchIPs();
    } catch (error: any) {
        if (error.response && error.response.status === 401) return;
        const msg = error.response?.data?.message || 'Operation failed';
        alert(msg);
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
      let statusClass = "bg-white border border-gray-300 hover:border-gray-500 cursor-pointer"; // Free
      
      if (existing) {
        statusClass = "bg-black border-black cursor-not-allowed"; // Active
        if (existing.status === 'reserved') statusClass = "bg-orange-500 border-orange-500 cursor-not-allowed";
      }
      
      // Network/Broadcast
      if (i === 0 || i === 255) statusClass = "bg-gray-200 border-gray-200 cursor-not-allowed opacity-50";

      cells.push(
        <div 
          key={i} 
          title={existing ? `${currentIP} (${existing.hostname || existing.status})` : currentIP}
          className={`w-3 h-3 rounded-[2px] ${statusClass} transition-all duration-200`}
          onClick={() => {
             if (i !== 0 && i !== 255) {
                 handleInteraction(currentIP, existing?.id);
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
                <span key={ip.id} className={`text-white text-xs px-2 py-1 rounded-md font-medium ${ip.status === 'reserved' ? 'bg-orange-500' : 'bg-black'}`}>
                    {ip.address}
                </span>
            ))}
        </div>
         <div className="mt-2 text-xs text-gray-400">List view is read-only for now.</div>
       </div>
    );
  }

  return (
    <div className={`mt-6 p-6 rounded-xl border border-gray-100 transition-colors duration-300 ${reservationMode ? 'bg-orange-50/50' : 'bg-gray-50/50'}`}>
      <div className="flex justify-between items-center mb-4">
        <div className="flex gap-4 text-xs font-medium text-gray-500">
            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] border border-gray-300 bg-white"></div> Free</span>
            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] bg-black"></div> Active</span>
            <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] bg-orange-500"></div> Reserved</span>
        </div>
        
        <div className="flex items-center gap-4">
            {/* Mode Toggle */}
            <button
                onClick={() => setReservationMode(!reservationMode)}
                className={`flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium transition-all ${
                    reservationMode 
                    ? 'bg-orange-100 text-orange-700 ring-1 ring-orange-200' 
                    : 'text-gray-500 hover:text-gray-900'
                }`}
                title="Toggle Reservation Mode"
            >
                {reservationMode ? <ShieldCheck size={14} /> : <Shield size={14} />}
                {reservationMode ? 'Reservation Mode ON' : 'Reserve IP'}
            </button>

            {!reservationMode && (
                <button
                onClick={() => handleInteraction()}
                disabled={allocating}
                className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg text-xs font-semibold hover:bg-gray-800 transition-all shadow-sm active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed"
                >
                {allocating ? <RefreshCw size={14} className="animate-spin" /> : <Plus size={14} />}
                Allocate Next
                </button>
            )}
        </div>
      </div>

      <div className="grid grid-cols-16 gap-1 w-fit mx-auto">
        {cells}
      </div>
    </div>
  );
}
