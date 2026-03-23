# proxy_manager.py
import threading
import time
import random
import requests
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import Config

class ProxyManager:
    def __init__(self):
        self.proxy_list = []
        self.proxy_stats = {}
        self.lock = threading.Lock()
        self.running = True
        self.last_refresh = 0
        
        # Inisialisasi
        self.download_proxies()
        
        # Start background threads
        self.start_auto_refresh()
        self.start_health_checker()
    
    def _init_stats(self):
        """Inisialisasi statistik proxy baru"""
        return {
            'success': 0,
            'fail': 0,
            'total_time': 0,
            'avg_time': 1.0,
            'last_used': 0,
            'consecutive_fails': 0,
            'weight': 1.0,
            'status': 'unknown'  # unknown, good, bad, dead
        }
    
    def _calculate_weight(self, stats):
        """Hitung bobot berdasarkan performa"""
        total = stats['success'] + stats['fail']
        if total == 0:
            return 1.0
        
        # Success rate (0-1)
        success_rate = stats['success'] / total
        
        # Speed score (semakin cepat semakin tinggi)
        speed_score = 1.0 / stats['avg_time'] if stats['avg_time'] > 0 else 1.0
        speed_score = min(speed_score, 2.0)
        
        # Weight = (success_rate * 0.7) + (speed_score * 0.3)
        weight = (success_rate * 0.7) + (speed_score * 0.3)
        
        # Bonus untuk proxy yang pernah sukses
        if stats['success'] > 0:
            weight *= 1.5
        
        # Status-based adjustments
        if stats['status'] == 'dead':
            weight *= 0.1
        elif stats['status'] == 'bad':
            weight *= 0.5
        
        # Gunakan nilai dari config
        return max(Config.PROXY_MIN_WEIGHT, min(Config.PROXY_MAX_WEIGHT, weight))
    
    def download_proxies(self):
        """Download proxy dari multiple sources"""
        try:
            all_proxies = []
            
            for source in Config.PROXY_SOURCES:
                try:
                    headers = {"User-Agent": "Mozilla/5.0"}
                    response = requests.get(source, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        proxies = [line.strip() for line in response.text.split('\n') if line.strip()]
                        
                        formatted_count = 0
                        for proxy in proxies:
                            # Skip SOCKS
                            if proxy.startswith('socks'):
                                continue
                            
                            # Format proxy
                            if proxy.startswith('http://') or proxy.startswith('https://'):
                                all_proxies.append(proxy)
                                formatted_count += 1
                            elif ':' in proxy and not proxy.startswith('http'):
                                all_proxies.append(f"http://{proxy}")
                                formatted_count += 1
                        
                        if Config.DEBUG:
                            print(f"[+] Loaded {formatted_count} proxies from {source[:50]}")
                        
                except Exception as e:
                    if Config.DEBUG:
                        print(f"[-] Error from {source[:50]}: {e}")
                    continue
            
            # Remove duplicates
            all_proxies = list(dict.fromkeys(all_proxies))
            
            # Batasi jumlah sesuai config
            if len(all_proxies) > Config.PROXY_MAX_TOTAL:
                all_proxies = all_proxies[:Config.PROXY_MAX_TOTAL]
                print(f"[+] Limited to {Config.PROXY_MAX_TOTAL} proxies")
            
            with self.lock:
                # Reset stats untuk proxy baru
                old_proxies = set(self.proxy_list)
                new_proxies = set(all_proxies)
                
                # Hapus proxy yang tidak ada di list baru
                for proxy in old_proxies - new_proxies:
                    if proxy in self.proxy_stats:
                        del self.proxy_stats[proxy]
                
                # Tambah proxy baru
                self.proxy_list = all_proxies
                for proxy in new_proxies - old_proxies:
                    self.proxy_stats[proxy] = self._init_stats()
            
            print(f"[+] Proxy Manager: {len(self.proxy_list)} proxies ready")
            if Config.DEBUG and self.proxy_list:
                print(f"[+] Example: {self.proxy_list[0]}")
            return self.proxy_list
            
        except Exception as e:
            print(f"[-] Proxy download error: {e}")
            return self.proxy_list
    
    def get_proxy(self):
        """Dapatkan proxy terbaik berdasarkan statistik real-time"""
        with self.lock:
            if not self.proxy_list:
                return None
            
            # Filter proxy yang masih hidup
            alive_proxies = []
            for proxy in self.proxy_list:
                if proxy not in self.proxy_stats:
                    self.proxy_stats[proxy] = self._init_stats()
                    alive_proxies.append(proxy)
                else:
                    stats = self.proxy_stats[proxy]
                    
                    # Proxy dianggap mati jika gagal 5 kali berturut
                    if stats['consecutive_fails'] < Config.PROXY_MAX_FAILURES:
                        # Update bobot
                        stats['weight'] = self._calculate_weight(stats)
                        alive_proxies.append(proxy)
            
            if not alive_proxies:
                # Semua proxy mati, reset status
                print("[!] All proxies dead, resetting stats...")
                for proxy in self.proxy_list[:100]:
                    if proxy in self.proxy_stats:
                        self.proxy_stats[proxy] = self._init_stats()
                alive_proxies = self.proxy_list[:100]
            
            # Weighted random selection
            return self._weighted_choice(alive_proxies)
    
    def _weighted_choice(self, proxies):
        """Pilih proxy dengan weighted random"""
        total_weight = sum(self.proxy_stats[p]['weight'] for p in proxies if p in self.proxy_stats)
        
        if total_weight == 0:
            proxy = random.choice(proxies)
            return {"http": proxy, "https": proxy}
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for proxy in proxies:
            if proxy in self.proxy_stats:
                cumulative += self.proxy_stats[proxy]['weight']
                if r <= cumulative:
                    return {"http": proxy, "https": proxy}
        
        # Fallback
        proxy = random.choice(proxies)
        return {"http": proxy, "https": proxy}
    
    def update_stats(self, proxy_url, success, response_time=None):
        """Update statistik berdasarkan hasil request REAL"""
        with self.lock:
            if proxy_url not in self.proxy_stats:
                self.proxy_stats[proxy_url] = self._init_stats()
            
            stats = self.proxy_stats[proxy_url]
            stats['last_used'] = time.time()
            
            if success:
                # Request sukses
                stats['success'] += 1
                stats['consecutive_fails'] = 0
                
                if stats['status'] == 'dead':
                    stats['status'] = 'good'
                
                if response_time:
                    total = stats['total_time'] + response_time
                    count = stats['success'] + stats['fail']
                    stats['avg_time'] = total / count if count > 0 else response_time
                    stats['total_time'] = total
            else:
                # Request gagal
                stats['fail'] += 1
                stats['consecutive_fails'] += 1
                
                if stats['consecutive_fails'] >= Config.PROXY_MAX_FAILURES:
                    stats['status'] = 'dead'
                    if Config.DEBUG:
                        print(f"[!] Proxy marked as dead: {proxy_url[:60]}")
            
            # Update status berdasarkan success rate
            total = stats['success'] + stats['fail']
            if total >= 10:
                success_rate = stats['success'] / total
                if success_rate < 0.1:
                    stats['status'] = 'bad'
                elif success_rate > 0.5:
                    stats['status'] = 'good'
            
            stats['weight'] = self._calculate_weight(stats)
    
    def start_auto_refresh(self):
        """Refresh proxy list secara periodik"""
        def refresh_worker():
            while self.running:
                time.sleep(Config.PROXY_REFRESH_INTERVAL)
                print("\n[*] Refreshing proxy list...")
                self.download_proxies()
        
        refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        refresh_thread.start()
    
    def start_health_checker(self):
        """Background thread untuk cek kesehatan proxy mati"""
        def health_check_worker():
            while self.running:
                time.sleep(300)  # Setiap 5 menit
                
                with self.lock:
                    # Ambil proxy yang mati
                    dead_proxies = [
                        p for p in self.proxy_list[:50]
                        if p in self.proxy_stats and self.proxy_stats[p]['status'] == 'dead'
                    ]
                
                if dead_proxies:
                    print(f"[*] Checking {len(dead_proxies)} dead proxies...")
                    
                    # Test parallel
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        futures = {executor.submit(self._quick_test, proxy): proxy for proxy in dead_proxies}
                        
                        for future in as_completed(futures):
                            proxy = futures[future]
                            try:
                                is_alive = future.result()
                                if is_alive:
                                    with self.lock:
                                        if proxy in self.proxy_stats:
                                            self.proxy_stats[proxy]['status'] = 'good'
                                            self.proxy_stats[proxy]['consecutive_fails'] = 0
                                            print(f"[+] Proxy revived: {proxy[:60]}")
                            except:
                                pass
        
        checker = threading.Thread(target=health_check_worker, daemon=True)
        checker.start()
    
    def _quick_test(self, proxy):
        """Test cepat apakah proxy hidup - DITAMBAHKAN"""
        try:
            response = requests.get(
                "http://httpbin.org/ip",
                proxies={"http": proxy, "https": proxy},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def print_stats(self):
        """Tampilkan statistik proxy (top 10)"""
        print("\n" + "="*60)
        print("PROXY STATISTICS (Top 10 by Weight)")
        print("="*60)
        
        with self.lock:
            # Sort by weight
            sorted_proxies = sorted(
                [(p, s) for p, s in self.proxy_stats.items() if p in self.proxy_list],
                key=lambda x: x[1]['weight'],
                reverse=True
            )[:10]
            
            for proxy, stats in sorted_proxies:
                total = stats['success'] + stats['fail']
                if total > 0:
                    success_rate = (stats['success'] / total) * 100
                    status_icon = {
                        'good': '✓',
                        'bad': '⚠',
                        'dead': '✗',
                        'unknown': '?'
                    }.get(stats['status'], '?')
                    
                    print(f"{status_icon} {proxy[:55]}")
                    print(f"   ✓ Success: {stats['success']} | ✗ Fail: {stats['fail']}")
                    print(f"   📊 Rate: {success_rate:.1f}% | Time: {stats['avg_time']:.2f}s")
                    print(f"   ⚖ Weight: {stats['weight']:.2f} | Status: {stats['status']}")
                    print()
    
    def get_stats_summary(self):
        """Dapatkan ringkasan statistik"""
        with self.lock:
            total = len(self.proxy_list)
            good = sum(1 for p in self.proxy_list if p in self.proxy_stats and self.proxy_stats[p]['status'] == 'good')
            bad = sum(1 for p in self.proxy_list if p in self.proxy_stats and self.proxy_stats[p]['status'] == 'bad')
            dead = sum(1 for p in self.proxy_list if p in self.proxy_stats and self.proxy_stats[p]['status'] == 'dead')
            unknown = total - good - bad - dead
            
            return {
                'total': total,
                'good': good,
                'bad': bad,
                'dead': dead,
                'unknown': unknown
            }
    
    def cleanup(self):
        """Bersihkan resources"""
        self.running = False
