# Upbit Terminology Glossary / 업비트 용어 사전

Use the terms below according to the user's language.
사용자 언어에 맞게 아래 용어를 사용하라.

---

## Core Trading Terms / 핵심 거래 용어

| English | 한국어 |
|---|---|
| Market / Trading pair | 페어 / 거래쌍 |
| Market pair format | `{QUOTE}-{BASE}` 형식 (예: `KRW-BTC`) — 타 거래소의 `BTC/KRW` 와 순서 반대 |
| Ticker / Current price | 현재가 |
| Orderbook | 호가 |
| Orderbook instruments | 호가 정책 |
| Candle (OHLCV) | 캔들 |
| Recent trades | 체결 내역 |
| Account balance | 잔고 |
| Order | 주문 |
| Trade | 체결 |
| Open / Unfilled | 미체결 |

---

## Order / 주문 관련

| English | 한국어 | 비고 |
|---|---|---|
| Buy / Bid | 매수 | `side=bid` |
| Sell / Ask | 매도 | `side=ask` |
| Limit order | 지정가 | `ord_type=limit` |
| Market buy (by amount) | 시장가 매수 | `ord_type=price`, 금액 기준 |
| Market sell (by volume) | 시장가 매도 | `ord_type=market`, 수량 기준 |
| Best price order | 최유리 지정가 | `ord_type=best` |
| Order unit price | 주문 단가 | `price` 필드 |
| Order volume | 주문 수량 | `volume` 필드 |
| Time in force | 체결 조건 | `time_in_force` |
| IOC (Immediate or Cancel) | 즉시 체결 또는 취소 | `time_in_force=ioc` |
| FOK (Fill or Kill) | 전량 체결 또는 취소 | `time_in_force=fok` |
| Post only | 메이커 전용 | `time_in_force=post_only` |
| SMP (Self-Match Prevention) | 자전거래 방지 | `smp_type` |
| Watch order / Stop order | 예약 주문 | `state=watch` |
| Wait (pending) | 체결 대기 | `state=wait` |
| Done | 체결 완료 | `state=done` |
| Cancelled | 주문 취소 | `state=cancel` |
| Order availability / Chance | 주문 가능 정보 | 수수료율, 최소 주문 금액 등 |
| Fee | 수수료 | `bid_fee` (매수), `ask_fee` (매도) |
| Reserved fee | 예약 수수료 | `reserved_fee` |
| Paid fee | 지불 수수료 | `paid_fee` |
| Remaining fee | 잔여 수수료 | `remaining_fee` |
| Batch cancel | 일괄 취소 | `orders cancel-open` |

---

## Deposits & Withdrawals / 입출금 관련

| English | 한국어 | 비고 |
|---|---|---|
| Deposit | 입금 | |
| Withdrawal / Withdraw | 출금 | ※ "withdrawal" 대신 "withdraw" 사용 |
| Deposit address | 입금 주소 | |
| Allowed withdrawal address | 출금 허용 주소 | 사전 등록 필요 |
| Network / Net type | 네트워크 | `net_type` 필드 |
| Two-factor authentication | 2차 인증 | `two_factor_type` |
| Kakao authentication | 카카오 인증 | `two_factor_type=kakao` |
| Naver authentication | 네이버 인증 | `two_factor_type=naver` |
| Hana certificate authentication | 하나 인증 | `two_factor_type=hana` |
| Secondary address | 보조 주소 | Destination Tag / Memo |
| Internal (instant) withdrawal | 즉시 출금 | `transaction_type=internal` |
| Processing | 처리 중 | `PROCESSING` |
| Accepted / Completed | 완료 | `ACCEPTED` |
| Cancelled | 취소됨 | `CANCELLED` |
| Rejected | 반려됨 | `REJECTED` |
| Travel Rule suspected | 트래블룰 심사 중 | `TRAVEL_RULE_SUSPECTED` |
| Refunding | 반환 중 | `REFUNDING` |
| Refunded | 반환 완료 | `REFUNDED` |

---

## Travel Rule / 트래블룰

| English | 한국어 | 비고 |
|---|---|---|
| Travel Rule verification | 계정주 확인 | |
| VASP list | 거래소 목록 | Virtual Asset Service Provider |
| Verify by deposit TxID | 입금 TxID 검증 | |
| Verify by deposit UUID | 입금 UUID 검증 | |

---

## Market Data / 시세

| English | 한국어 | 비고 |
|---|---|---|
| Trade price | 현재가 | `trade_price` |
| Previous closing price | 전일 종가 | `prev_closing_price` |
| Price direction | 등락 방향 | `change`: RISE / EVEN / FALL |
| Price change | 등락폭 | `change_price` |
| Change rate | 등락률 | `change_rate` |
| 52-week high/low | 52주 최고/최저 | `highest_52_week_price` |
| Accumulated trade value | 누적 거래대금 | `acc_trade_price_24h` |
| Accumulated trade volume | 누적 거래량 | `acc_trade_volume_24h` |
| Trade initiator | 체결 주체 | `ask_bid`: ASK(매도자) / BID(매수자) |

---

## Account / 잔고

| English | 한국어 | 비고 |
|---|---|---|
| Balance | 보유 잔고 | `balance` (주문 미반영) |
| Locked balance | 잠금 잔고 | `locked` (주문/출금 잠김) |
| Total holdings | 총 보유량 | `balance + locked` |
| Average buy price | 매수 평균가 | `avg_buy_price` |
| Quote currency / Unit currency | 결제 화폐 | `unit_currency` |

---

## Wallet Status / 입출금 서비스 상태

| English | 한국어 |
|---|---|
| Working | 정상 |
| Deposit only | 입금만 가능 |
| Withdraw only | 출금만 가능 |
| Paused | 점검 중 |
| Unsupported | 미지원 |
