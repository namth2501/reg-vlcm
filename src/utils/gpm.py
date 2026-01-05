import aiohttp
import asyncio
from typing import Optional, List, Dict, Any, Literal
from enum import IntEnum


class SortType(IntEnum):
    Newest = 0
    Oldest = 1
    NameAZ = 2
    NameZA = 3


class DeleteMode(IntEnum):
    Database = 1
    DatabaseAndStorage = 2


class ProxyType:
    HTTP = 'http'
    SOCKS5 = 'socks5'
    TMProxy = 'tmproxy'
    TinProxy = 'tinproxy'
    TinsoftProxy = 'tinsoftproxy'


class GpmLoginClient:
    def __init__(self, host: str = '127.0.0.1', port: int = 19995):
        self.base_url = f"http://{host}:{port}/api/v3"
        self.timeout = aiohttp.ClientTimeout(total=30)

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to GPM API"""
        url = f"{self.base_url}{endpoint}"
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.request(method, url, params=params, json=json_data) as response:
                return await response.json()

    async def get_profiles(
        self,
        group_id: Optional[str | int] = None,
        page: int = 1,
        per_page: int = 50,
        sort: SortType = SortType.Newest,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get list of profiles"""
        params: Dict[str, Any] = {
            'page': page,
            'per_page': per_page,
            'sort': sort.value
        }
        
        if group_id is not None:
            params['group'] = group_id
        
        if search:
            params['search'] = search
        
        return await self._request('GET', '/profiles', params=params)

    async def get_profile(self, profile_id: str) -> Dict[str, Any]:
        """Get a single profile by ID"""
        return await self._request('GET', f'/profiles/{profile_id}')

    async def create_profile(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new profile"""
        return await self._request('POST', '/profiles/create', json_data=options)

    async def update_profile(self, profile_id: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing profile"""
        return await self._request('POST', f'/profiles/update/{profile_id}', json_data=options)

    async def delete_profile(self, profile_id: str, mode: DeleteMode = DeleteMode.DatabaseAndStorage) -> Dict[str, Any]:
        """Delete a profile"""
        params = {'mode': mode.value}
        return await self._request('GET', f'/profiles/delete/{profile_id}', params=params)

    async def start_profile(self, profile_id: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Start a profile and get browser connection details"""
        params: Dict[str, Any] = {}
        
        if options:
            if 'addination_args' in options:
                params['addination_args'] = options['addination_args']
            if 'win_scale' in options:
                params['win_scale'] = options.get('win_scale', 0.6)
            if 'win_pos' in options:
                params['win_pos'] = options['win_pos']
           
        params['win_size'] = '1920,1080'
        return await self._request('GET', f'/profiles/start/{profile_id}', params=params)

    async def close_profile(self, profile_id: str) -> Dict[str, Any]:
        """Close a running profile"""
        return await self._request('GET', f'/profiles/close/{profile_id}')

    async def get_groups(self) -> Dict[str, Any]:
        """Get list of groups"""
        return await self._request('GET', '/groups')

    async def find_profile_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a profile by name"""
        result = await self.get_profiles(group_id=None, page=1, per_page=1000, sort=SortType.Newest, search=name)
        if result.get('success') and result.get('data'):
            for profile in result['data']:
                if profile.get('name') == name:
                    return profile
        return None

    async def find_group_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a group by name"""
        result = await self.get_groups()
        if result.get('success') and result.get('data'):
            for group in result['data']:
                if group.get('name') == name:
                    return group
        return None

    async def update_proxy(self, profile_id: str, proxy: str) -> Dict[str, Any]:
        """Update proxy for a profile"""
        return await self.update_profile(profile_id, {
            'profile_name': '',
            'raw_proxy': proxy
        })

    async def clear_proxy(self, profile_id: str) -> Dict[str, Any]:
        """Clear proxy for a profile"""
        return await self.update_proxy(profile_id, '')

    def format_proxy(self, config: Dict[str, Any]) -> str:
        """Format proxy config to string"""
        proxy_type = config.get('type', 'http')
        host = config.get('host')
        port = config.get('port')
        
        if not host or not port:
            return ''
        
        if proxy_type == ProxyType.HTTP:
            username = config.get('username')
            password = config.get('password')
            if username and password:
                return f"{host}:{port}:{username}:{password}"
            return f"{host}:{port}"
        
        elif proxy_type == ProxyType.SOCKS5:
            username = config.get('username')
            password = config.get('password')
            auth = f"{username}:{password}@" if username and password else ''
            return f"socks5://{auth}{host}:{port}"
        
        elif proxy_type == ProxyType.TMProxy:
            api_key = config.get('apiKey')
            return f"tm://{api_key}:true" if api_key else ''
        
        elif proxy_type == ProxyType.TinProxy:
            api_key = config.get('apiKey')
            return f"tin://{api_key}:true" if api_key else ''
        
        elif proxy_type == ProxyType.TinsoftProxy:
            api_key = config.get('apiKey')
            return f"tinsoft://{api_key}:true" if api_key else ''
        
        return ''

    def parse_proxy(self, proxy_string: str) -> Optional[Dict[str, Any]]:
        """Parse proxy string to config"""
        if not proxy_string or not proxy_string.strip():
            return None
        
        proxy_string = proxy_string.strip()
        
        if proxy_string.startswith('socks5://'):
            url = proxy_string.replace('socks5://', '')
            parts = url.split('@')
            if len(parts) == 2:
                auth = parts[0].split(':')
                host_port = parts[1].split(':')
                return {
                    'type': ProxyType.SOCKS5,
                    'host': host_port[0],
                    'port': int(host_port[1]),
                    'username': auth[0],
                    'password': auth[1]
                }
            else:
                host_port = parts[0].split(':')
                return {
                    'type': ProxyType.SOCKS5,
                    'host': host_port[0],
                    'port': int(host_port[1])
                }
        
        if proxy_string.startswith('http://'):
            url = proxy_string.replace('http://', '')
            parts = url.split(':')
            if len(parts) >= 4:
                return {
                    'type': ProxyType.HTTP,
                    'host': parts[0],
                    'port': int(parts[1]),
                    'username': parts[2],
                    'password': parts[3]
                }
            elif len(parts) >= 2:
                return {
                    'type': ProxyType.HTTP,
                    'host': parts[0],
                    'port': int(parts[1])
                }
            return None
        
        if proxy_string.startswith('tm://'):
            api_key = proxy_string.split('://')[1].split(':')[0]
            return {
                'type': ProxyType.TMProxy,
                'apiKey': api_key
            }
        
        if proxy_string.startswith('tin://'):
            api_key = proxy_string.split('://')[1].split(':')[0]
            return {
                'type': ProxyType.TinProxy,
                'apiKey': api_key
            }
        
        if proxy_string.startswith('tinsoft://'):
            api_key = proxy_string.split('://')[1].split(':')[0]
            return {
                'type': ProxyType.TinsoftProxy,
                'apiKey': api_key
            }
        
        # Try parsing as HTTP format (host:port:user:pass or host:port)
        parts = proxy_string.split(':')
        if len(parts) >= 4:
            return {
                'type': ProxyType.HTTP,
                'host': parts[0],
                'port': int(parts[1]),
                'username': parts[2],
                'password': parts[3]
            }
        elif len(parts) >= 2:
            return {
                'type': ProxyType.HTTP,
                'host': parts[0],
                'port': int(parts[1])
            }
        
        return None

    async def get_profile_proxy(self, profile_id: str) -> str:
        """Get proxy string for a profile"""
        result = await self.get_profile(profile_id)
        if result.get('success') and result.get('data'):
            return result['data'].get('raw_proxy', '')
        return ''

    async def find_profiles_by_proxy(self, proxy_string: str) -> List[Dict[str, Any]]:
        """Find all profiles using a specific proxy"""
        result = await self.get_profiles()
        if result.get('success') and result.get('data'):
            return [p for p in result['data'] if p.get('raw_proxy') == proxy_string]
        return []

    async def clear_proxy_from_all_profiles(self) -> Dict[str, List]:
        """Clear proxy from all profiles"""
        result = await self.get_profiles()
        success = []
        failed = []
        
        if result.get('success') and result.get('data'):
            for profile in result['data']:
                if profile.get('raw_proxy') and profile['raw_proxy'].strip():
                    try:
                        await self.clear_proxy(profile['id'])
                        success.append(profile)
                    except Exception as e:
                        failed.append({
                            'profile': profile,
                            'error': str(e)
                        })
        
        return {'success': success, 'failed': failed}

