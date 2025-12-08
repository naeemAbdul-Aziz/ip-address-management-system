import React, { useEffect, useState } from 'react';
import { Subnet, IPAddress, getSubnetIPs, allocateIP, reserveIP, releaseIp } from '../lib/api';
import { Plus, RefreshCw, Shield, ShieldCheck, Loader2 } from 'lucide-react';
import Modal from './ui/Modal';
import { useToast } from './ui/Toast';

interface SubnetGridProps {
  subnet: Subnet;
}

export default function SubnetGrid({ subnet }: SubnetGridProps) {
  const [ips, setIps] = useState<IPAddress[]>([]);
  const [loading, setLoading] = useState(false);
  const [reservationMode, setReservationMode] = useState(false);
  const toast = useToast();

  // Modal States
  const [selectedIP, setSelectedIP] = useState<IPAddress | null>(null);
  const [targetIPStr, setTargetIPStr] = useState<string | null>(null);
  
  const [showAllocateModal, setShowAllocateModal] = useState(false);
  const [deviceName, setDeviceName] = useState('');
  
  const [showReleaseModal, setShowReleaseModal] = useState(false);
  const [processing, setProcessing] = useState(false);

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

  // -- Handlers --

  const handleCellClick = async (ipAddress: string, existing?: IPAddress) => {
    // 1. Existing IP -> Confirm Release
    if (existing) {
        setSelectedIP(existing);
        setShowReleaseModal(true);
        return;
    }

    // 2. Reservation Mode -> Direct Reserve (No modal needed for quick parking)
    if (reservationMode) {
        try {
            setProcessing(true);
            await reserveIP(subnet.id, ipAddress, "Reserved via Admin UI");
            toast.success(`Reserved ${ipAddress}`);
            fetchIPs();
        } catch (error: any) {
            toast.error(error.response?.data?.message || 'Failed to reserve');
        } finally {
            setProcessing(false);
        }
        return;
    }

    // 3. Normal Mode -> Open Allocate Modal for Device Name
    // We only support "Next Available" via the big button, but maybe user clicked a specific empty cell?
    // For now, grid click on empty cell implies "Allocate THIS one" (not implemented in backend yet fully, defaults to next)
    // Actually, backend allocate only supports "Next Free". 
    // So clicking a specific empty cell might be confusing if we can't force that IP.
    // Let's stick to "Allocate Next" button for generic implementation, 
    // BUT if we want to allow picking specific slots, we need backend support.
    // Assuming backend allocates NEXT FREE, clicking a cell shouldn't trigger allocation unless it's the next one.
    // To safe-guard, let's keep Allocation Button as main entry, and maybe disable empty cell clicks for now unless in Reserve Mode.
    
    // UPDATE: "Allocate Next" button logic
  };

  const openAllocateModal = () => {
      setDeviceName('');
      setShowAllocateModal(true);
  };

  const handleAllocateSubmit = async () => {
      try {
          setProcessing(true);
          const res = await allocateIP(subnet.id, deviceName || undefined);
          toast.success(`Allocated ${res.address} to ${res.hostname || 'Device'}`);
          setShowAllocateModal(false);
          fetchIPs();
      } catch (error: any) {
          toast.error(error.response?.data?.message || 'Allocation failed');
      } finally {
          setProcessing(false);
      }
  };

  const handleReleaseSubmit = async () => {
      if (!selectedIP) return;
      try {
          setProcessing(true);
          await releaseIp(selectedIP.id);
          toast.success(`Released ${selectedIP.address}`);
          setShowReleaseModal(false);
          fetchIPs();
      } catch (error: any) {
          toast.error(error.response?.data?.message || 'Release failed');
      } finally {
          setProcessing(false);
      }
  };

  // -- Grid Rendering --
  
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
      const isNetworkBroadcast = i === 0 || i === 255;
      
      let statusClass = "bg-white border border-gray-300 hover:border-gray-500 cursor-pointer"; 
      if (existing) {
        statusClass = "bg-black border-black cursor-pointer hover:opacity-80"; 
        if (existing.status === 'reserved') statusClass = "bg-orange-500 border-orange-500 cursor-pointer hover:opacity-80";
      }
      if (isNetworkBroadcast) statusClass = "bg-gray-200 border-gray-200 cursor-not-allowed opacity-50";

      cells.push(
        <div 
          key={i} 
          title={existing ? `${currentIP} (${existing.hostname || existing.status})` : currentIP}
          className={`w-3 h-3 rounded-[2px] ${statusClass} transition-all duration-200`}
          onClick={() => {
             if (!isNetworkBroadcast) handleCellClick(currentIP, existing);
          }}
        />
      );
    }
  } else {
    // List logic fallback (omitted for brevity, keeping old list)
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
    <>
      <div className={`mt-6 p-6 rounded-xl border border-gray-100 transition-colors duration-300 ${reservationMode ? 'bg-orange-50/50' : 'bg-gray-50/50'}`}>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4 gap-4">
          <div className="flex gap-4 text-xs font-medium text-gray-500">
              <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] border border-gray-300 bg-white"></div> Free</span>
              <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] bg-black"></div> Active</span>
              <span className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-[2px] bg-orange-500"></div> Reserved</span>
          </div>
          
          <div className="flex items-center gap-4 w-full sm:w-auto justify-end">
              <button
                  onClick={() => setReservationMode(!reservationMode)}
                  className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                      reservationMode 
                      ? 'bg-orange-100 text-orange-700 ring-1 ring-orange-200 shadow-inner' 
                      : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300 hover:text-gray-900 shadow-sm'
                  }`}
              >
                  {reservationMode ? <ShieldCheck size={14} /> : <Shield size={14} />}
                  {reservationMode ? 'Reservation ON' : 'Reserve'}
              </button>

              {!reservationMode && (
                  <button
                  onClick={openAllocateModal}
                  className="flex items-center gap-2 bg-black text-white px-4 py-2 rounded-lg text-xs font-semibold hover:bg-gray-800 transition-all shadow-sm active:scale-95"
                  >
                  <Plus size={14} />
                  Allocate Next
                  </button>
              )}
          </div>
        </div>

        <div className="grid grid-cols-16 gap-1 w-fit mx-auto touch-manipulation">
          {cells}
        </div>
      </div>

      {/* Allocate Modal */}
      <Modal isOpen={showAllocateModal} onClose={() => setShowAllocateModal(false)} title="Allocate IP Address">
          <div className="space-y-4">
              <p className="text-sm text-gray-500">
                  This will allocate the next available IP address in <strong>{subnet.cidr}</strong>.
              </p>
              <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Device Name / Hostname (Optional)</label>
                  <input 
                      type="text" 
                      value={deviceName}
                      onChange={e => setDeviceName(e.target.value)}
                      placeholder="e.g. printer-floor-2"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black/5"
                      autoFocus
                  />
              </div>
              <div className="flex justify-end gap-3 mt-6">
                  <button onClick={() => setShowAllocateModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 font-medium">Cancel</button>
                  <button 
                      onClick={handleAllocateSubmit} 
                      disabled={processing}
                      className="px-4 py-2 bg-black text-white rounded-lg text-sm font-medium hover:bg-gray-800 disabled:opacity-50 flex items-center gap-2"
                  >
                      {processing && <Loader2 size={14} className="animate-spin" />}
                      Allocate
                  </button>
              </div>
          </div>
      </Modal>

      {/* Release Modal */}
      <Modal isOpen={showReleaseModal} onClose={() => setShowReleaseModal(false)} title="Release IP Address" type="danger">
          <div className="space-y-4">
              <p className="text-sm text-gray-600">
                  Are you sure you want to release <strong>{selectedIP?.address}</strong>?
              </p>
              {selectedIP && (
                  <div className="bg-red-50 p-3 rounded-lg border border-red-100">
                      <p className="text-xs text-red-700 font-medium pb-1">Current Assignment:</p>
                      <p className="text-sm text-red-900">{selectedIP.hostname || 'Unknown Device'} <span className="text-red-400">|</span> {selectedIP.status}</p>
                  </div>
              )}
              <p className="text-xs text-gray-500">This action cannot be undone. The IP will become available for new devices.</p>
              
              <div className="flex justify-end gap-3 mt-6">
                  <button onClick={() => setShowReleaseModal(false)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 font-medium">Cancel</button>
                  <button 
                      onClick={handleReleaseSubmit} 
                      disabled={processing}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
                  >
                      {processing && <Loader2 size={14} className="animate-spin" />}
                      Release IP
                  </button>
              </div>
          </div>
      </Modal>
    </>
  );
}
