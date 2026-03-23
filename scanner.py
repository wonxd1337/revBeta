# scanner.py - Tambahkan method ini
def reverse_ip_hackertarget(self, ip):
    """Reverse IP dengan auto-learning proxy dan fallback direct"""
    cache_key = f"ht_{ip}"
    cached = self.cache_manager.get_reverse_cache(cache_key)
    if cached:
        return cached
    
    max_proxy_attempts = 3
    
    # Strategy 1: Coba dengan proxy (belajar dari pengalaman)
    for attempt in range(max_proxy_attempts):
        proxy_dict = self.proxy_manager.get_proxy()
        proxy_used = list(proxy_dict.values())[0] if proxy_dict else None
        
        start_time = time.time()
        
        try:
            url = f"https://api.hackertarget.com/reverseiplookup/?q={ip}"
            headers = self.headers.copy()
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            
            response = self.session.get(
                url, 
                headers=headers, 
                proxies=proxy_dict,
                timeout=Config.TIMEOUT_REVERSE,
                verify=False
            )
            
            response_time = time.time() - start_time
            
            # UPDATE STATISTIK - SUKSES
            if proxy_used:
                self.proxy_manager.update_stats(proxy_used, True, response_time)
            
            if response.status_code == 200:
                if "error" not in response.text.lower():
                    domains = response.text.strip().split('\n')
                    domains = [d.strip() for d in domains if d.strip()]
                    
                    if domains:
                        self.cache_manager.save_reverse_cache(cache_key, domains, 'hackertarget')
                        return domains
                    return []
                    
        except Exception as e:
            # UPDATE STATISTIK - GAGAL
            if proxy_used:
                self.proxy_manager.update_stats(proxy_used, False)
            
            if attempt < max_proxy_attempts - 1:
                time.sleep(1)
                continue
    
    # Strategy 2: Fallback - coba tanpa proxy (direct)
    try:
        print(f"[*] All proxies failed, trying direct for {ip}")
        response = self.session.get(
            f"https://api.hackertarget.com/reverseiplookup/?q={ip}",
            headers=headers,
            timeout=Config.TIMEOUT_REVERSE + 10,
            verify=False
        )
        
        if response.status_code == 200 and "error" not in response.text.lower():
            domains = response.text.strip().split('\n')
            domains = [d.strip() for d in domains if d.strip()]
            
            if domains:
                self.cache_manager.save_reverse_cache(cache_key, domains, 'hackertarget')
                return domains
    except:
        pass
    
    return []

def reverse_ip_tntcode(self, ip):
    """Reverse IP via tntcode.com dengan auto-learning proxy"""
    cache_key = f"tnt_{ip}"
    cached = self.cache_manager.get_reverse_cache(cache_key)
    if cached:
        return cached
    
    max_attempts = 3
    
    for attempt in range(max_attempts):
        proxy_dict = self.proxy_manager.get_proxy()
        proxy_used = list(proxy_dict.values())[0] if proxy_dict else None
        
        start_time = time.time()
        
        try:
            url = f"https://domains.tntcode.com/ip/{ip}"
            headers = self.headers.copy()
            headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            
            response = self.session.get(
                url, 
                headers=headers, 
                proxies=proxy_dict,
                timeout=Config.TIMEOUT_REVERSE,
                verify=False
            )
            
            response_time = time.time() - start_time
            
            if proxy_used:
                self.proxy_manager.update_stats(proxy_used, True, response_time)
            
            domains = re.findall(r'<a href="/domain/(.+?)"', response.text)
            
            if domains:
                self.cache_manager.save_reverse_cache(cache_key, domains, 'tntcode')
                return domains
            return []
            
        except Exception as e:
            if proxy_used:
                self.proxy_manager.update_stats(proxy_used, False)
            
            if attempt < max_attempts - 1:
                time.sleep(1)
                continue
    
    return []