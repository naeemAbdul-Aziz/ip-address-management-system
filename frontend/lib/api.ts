import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Auth Interceptor
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Error handling (401 Redirect)
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            localStorage.removeItem('token');
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
            }
        }
        return Promise.reject(error);
    }
);

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

export const allocateIP = async (subnetId: number, hostname?: string) => {
    const response = await api.post<IPAddress>(`/subnets/${subnetId}/allocate`, { hostname });
    return response.data;
};

export const reserveIP = async (subnetId: number, address?: string, description?: string) => {
    const response = await api.post<IPAddress>(`/subnets/${subnetId}/reserve`, { address, description });
    return response.data;
};

export const getSuggestedCidr = async (namespaceId: number, prefix: number = 24) => {
    const response = await api.get<{ cidr: string }>(`/namespaces/${namespaceId}/suggest-cidr`, { params: { prefix } });
    return response.data;
};

export interface SearchResult {
    type: 'ip' | 'subnet';
    id: number;
    title: string;
    subtitle: string;
    link: string;
}

export const search = async (q: string) => {
    const response = await api.get<{ results: SearchResult[] }>('/search', { params: { q } });
    return response.data.results;
};

export const releaseIp = async (ipId: number): Promise<void> => {
    await api.delete(`/ips/${ipId}`);
};

export default api;

