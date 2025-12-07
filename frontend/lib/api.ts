import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export interface Namespace {
    id: number;
    name: string;
    cidr: string;
    created_at: string;
}

export interface Subnet {
    id: number;
    namespace_id: number;
    cidr: string;
    label: string;
    utilization: number;
    vlan_id?: number;
    location?: string;
}

export interface IPAddress {
    id: number;
    subnet_id: number;
    address: string;
    status: 'active' | 'reserved' | 'deprecated';
    hostname?: string;
    description?: string;
}

export const getNamespaces = async () => {
    const response = await api.get<Namespace[]>('/namespaces/');
    return response.data;
};

export const createNamespace = async (name: string, cidr: string) => {
    const response = await api.post<Namespace>('/namespaces/', { name, cidr });
    return response.data;
};

export const getSubnets = async (namespaceId: number) => {
    const response = await api.get<Subnet[]>('/subnets/', { params: { namespace_id: namespaceId } });
    return response.data;
};

export const createSubnet = async (
    namespaceId: number,
    cidr: string,
    label: string,
    vlan_id?: number,
    location?: string
) => {
    const response = await api.post<Subnet>('/subnets/', {
        namespace_id: namespaceId,
        cidr,
        label,
        vlan_id,
        location
    });
    return response.data;
};

export const getSubnetIPs = async (subnetId: number) => {
    const response = await api.get<IPAddress[]>(`/subnets/${subnetId}/ips`);
    return response.data;
};

export const allocateIP = async (subnetId: number) => {
    const response = await api.post<IPAddress>(`/subnets/${subnetId}/allocate`);
    return response.data;
};

export const getSuggestedCidr = async (namespaceId: number, prefix: number = 24) => {
    const response = await api.get<{ cidr: string }>(`/namespaces/${namespaceId}/suggest-cidr`, { params: { prefix } });
    return response.data;
};

export default api;

