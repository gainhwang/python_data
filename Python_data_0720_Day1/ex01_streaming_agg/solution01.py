#Day1 실습 1
# -----------------------------------
# 앞 5줄만 출력해서 컬럼 이름과 형태를 확인


with open('data/web_logs.csv', encoding="utf-8") as f:
    for i, line in enumerate(f):
        print(line.strip())
        if i >= 4:
            break 


import csv

def read_logs(path):
    """한 줄씩 읽어 dict로 흘려보내는 제너레이터"""
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


# 확인: 앞 3건만 꺼내보기
gen = read_logs('data/web_logs.csv')
for _ in range(3):
    print(next(gen))

# 총 건수 카운팅
from collections import Counter

status_counter = Counter()
total = 0

for row in read_logs('data/web_logs.csv'):
    total += 1
    status_counter[row['status']] += 1

print('총 건수: ', total)
print(status_counter.most_common(5))


# 지표 증가
from collections import Counter, defaultdict

total = 0
by_status = Counter()
by_path = Counter()
by_hour = Counter()
by_ip = Counter()

for row in read_logs('data/web_logs.csv'):
    total += 1
    by_status[row['status']] += 1
    by_path[row['path']] += 1
    by_ip[row['ip']] += 1
    hour = row['timestamp'][11:13]
    by_hour[hour] += 1

# 비율 계산 (int로 변환)
err_5xx = sum(c for s, c in by_status.items() if str(s).startswith('5'))
ratio = err_5xx / total * 100
print(f'5xx: {err_5xx}건 ({ratio:.1f}%)')

# fold 패턴
from functools import reduce
from collections import Counter

def fold(acc, row):
    acc['total'] += 1
    acc['status'][row['status']] += 1
    return acc

init = {'total': 0, 'status': Counter()}
result = reduce(fold, read_logs('data/web_logs.csv'), init)
print(result['total'])

# 예쁘게 출력
print('=' * 40)
print(f'총 요청 수 : {total:,}')
print(f'5xx 오류율 : {ratio:.1f}%')
print('-- 인기 경로 TOP 5 --')
for path, cnt in by_path.most_common(5):
    print(f' {path:<20} {cnt:>7,}')
print('-- 접속 상위 IP TOP 5 --')
for ip, cnt in by_ip.most_common(5):
    print(f' {ip:<20} {cnt:>7,}')