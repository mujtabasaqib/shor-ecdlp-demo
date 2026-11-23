#!/usr/bin/env python3
"""
Q = d*G demo: why classical guessing is hopeless and why Shor isn't.

Act 1: Forward direction on real secp256k1 (easy and instant).
Act 2: Toy Shor for ECDLP, classically simulated on a tiny curve (it works,
       but the simulation needs n^2 memory, so it cannot scale).
Act 3: Brute-force guessing d on real secp256k1 (an endless loop).

Requires: numpy   (pip install numpy)
Usage:    python shor_ecdlp_demo.py            # all acts
          python shor_ecdlp_demo.py --every 1  
          python shor_ecdlp_demo.py --skip-loop
Stop Act 3 with Ctrl+C.
"""
import argparse
import math
import random
import sys
import time

import numpy as np

# ---------------------------------------------------------------------------
# Elliptic curve arithmetic: y^2 = x^3 + 7 (mod p). None = point at infinity.
# ---------------------------------------------------------------------------

def ec_add(P, Q, p):
    if P is None:
        return Q
    if Q is None:
        return P
    x1, y1 = P
    x2, y2 = Q
    if x1 == x2 and (y1 + y2) % p == 0:
        return None
    if P == Q:
        lam = (3 * x1 * x1) * pow(2 * y1, -1, p) % p
    else:
        lam = (y2 - y1) * pow(x2 - x1, -1, p) % p
    x3 = (lam * lam - x1 - x2) % p
    y3 = (lam * (x1 - x3) - y1) % p
    return (x3, y3)


def ec_mul(k, P, p):
    """Double-and-add: this is the EASY direction, Q = k*P."""
    R = None
    while k > 0:
        if k & 1:
            R = ec_add(R, P, p)
        P = ec_add(P, P, p)
        k >>= 1
    return R


# Real Bitcoin / Ethereum curve parameters (secp256k1)
SECP_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP_G = (
    0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
    0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
)


# ---------------------------------------------------------------------------
# Act 1: the easy direction
# ---------------------------------------------------------------------------

def act1():
    print("=" * 70)
    print("ACT 1: Q = d*G on real secp256k1 (the easy direction)")
    print("=" * 70)
    d = random.randrange(2, SECP_N)
    t = time.perf_counter()
    Q = ec_mul(d, SECP_G, SECP_P)
    dt = (time.perf_counter() - t) * 1000
    print(f"private key d : {hex(d)}")
    print(f"public key Qx : {hex(Q[0])}")
    print(f"public key Qy : {hex(Q[1])}")
    print(f"Computed in {dt:.2f} ms. Going backwards from Q to d? Keep reading...\n")
    return Q


# ---------------------------------------------------------------------------
# Act 2: toy Shor for ECDLP (classical simulation of the quantum circuit)
# ---------------------------------------------------------------------------

def is_prime(n):
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True


def find_toy_curve(min_order=50):
    """Find a small prime p where y^2 = x^3 + 7 has PRIME group order n.
    Then every non-infinity point is a generator."""
    p = min_order
    while True:
        p += 1
        if not is_prime(p) or p % 3 != 1:
            continue
        pts = [(x, y) for x in range(p) for y in range(p)
               if (y * y - x ** 3 - 7) % p == 0]
        n = len(pts) + 1  # +1 for infinity
        if n >= min_order and is_prime(n):
            return p, n, pts[0]


def shor_ecdlp_toy(p, n, G, Q, verbose=True):
    """
    Simulates Shor's ECDLP algorithm.

      1. Superpose all (a, b) in Z_n x Z_n.
      2. Compute f(a, b) = a*G + b*Q into a second register.
      3. Measure that register: state collapses to all (a, b) on a line
         a + b*d = c (mod n).
      4. Apply the 2D quantum Fourier transform.
      5. Measure (j, k). Interference leaves only outcomes with
         k = j*d (mod n).
      6. Classical post-processing: d = k * j^-1 mod n (extended Euclid).

    We fake the quantum computer with a state vector of n*n amplitudes.
    That memory cost is exactly why classical simulation can't scale.
    """
    Gm = [None] * n
    Qm = [None] * n
    for i in range(n):
        Gm[i] = ec_mul(i, G, p)
        Qm[i] = ec_mul(i, Q, p)

    # Step 1+2: build f(a,b) over the whole grid (needs only G and Q, never d)
    ids, F = {}, np.zeros((n, n), dtype=np.int64)
    for a in range(n):
        for b in range(n):
            pt = ec_add(Gm[a], Qm[b], p)
            F[a, b] = ids.setdefault(pt, len(ids))

    attempts = 0
    while True:
        attempts += 1
        # Step 3: measure the output register -> collapse input register
        c = F[random.randrange(n), random.randrange(n)]
        state = (F == c).astype(complex)
        state /= np.linalg.norm(state)

        # Step 4: 2D QFT
        state = np.fft.fft2(state) / n

        # Step 5: measure (j, k)
        probs = (np.abs(state) ** 2).ravel()
        probs /= probs.sum()
        idx = np.random.choice(n * n, p=probs)
        j, k = divmod(int(idx), n)
        if verbose:
            print(f"  [quantum run {attempts}] measured (j={j}, k={k})")

        if j == 0:
            if verbose:
                print("  j = 0 gives no information. Re-running the circuit...")
            continue

        # Step 6: solve k = j*d mod n
        d = (k * pow(j, -1, n)) % n
        if ec_mul(d, G, p) == Q:
            return d, attempts


def act2():
    print("=" * 70)
    print("ACT 2: Toy Shor on a tiny curve (simulated quantum computer)")
    print("=" * 70)
    p, n, G = find_toy_curve()
    d_secret = random.randrange(2, n)
    Q = ec_mul(d_secret, G, p)
    print(f"Toy curve: y^2 = x^3 + 7 over F_{p}, group order n = {n}")
    print(f"G = {G}, Q = {Q}   (secret d hidden from the solver)\n")

    t = time.perf_counter()
    d_found, runs = shor_ecdlp_toy(p, n, G, Q)
    dt = time.perf_counter() - t
    print(f"\nRecovered d = {d_found} in {runs} run(s), {dt:.2f}s "
          f"(true d = {d_secret}) -> {'MATCH' if d_found == d_secret else 'FAIL'}")

    mem_gb = (SECP_N ** 2) * 16 / 1e9
    print(f"\nSimulation state vector here: {n}x{n} = {n*n:,} amplitudes.")
    print(f"For secp256k1 it would be n^2 ~ 2^512 amplitudes "
          f"(~{mem_gb:.1e} GB). Your laptop declines the invitation.")
    print("A REAL quantum computer needs only ~thousands of logical qubits "
          "instead.\nThat gap is the entire threat.\n")


# ---------------------------------------------------------------------------
# Act 3: the futile brute-force loop
# ---------------------------------------------------------------------------

PUNS = [
    "Guess #{n:,}: wrong. This key is no pushover, it's a hard-pressed secret.",
    "Guess #{n:,}: not the key. I'm elliptic-ally challenged.",
    "Guess #{n:,}: nope. My success rate is curve-ing toward zero.",
    "Guess #{n:,}: miss. That's the point-less part of point addition.",
    "Guess #{n:,}: wrong again. I'm having a modular meltdown.",
    "Guess #{n:,}: nothing. Don't worry, I'll be d-termined.",
    "Guess #{n:,}: failed. This brute force is more of a brute mild breeze.",
    "Guess #{n:,}: no luck. I'm in a qubit of trouble without a quantum computer.",
    "Guess #{n:,}: wrong. Shor is on vacation, so I'm just Shor-ting myself.",
    "Guess #{n:,}: incorrect. At this rate the sun burns out first, no hash-tag needed.",
    "Guess #{n:,}: nope. Satoshi is sleeping soundly, not even a nonce-ense.",
    "Guess #{n:,}: wrong. I'm going in circles, but at least they're not ECC circles.",
    "Guess #{n:,}: whiff. My odds are looking pretty prime... as in 'prime-ly hopeless'.",
    "Guess #{n:,}: no. My hash-rate is just a hash-trickle.",
]


def act3(Q, every):
    print("=" * 70)
    print("ACT 3: Brute-forcing secp256k1 by guessing d = 1, 2, 3, ...")
    print("        (Ctrl+C to stop. Spoiler: you will stop first.)")
    print("=" * 70)
    total = SECP_N
    P = SECP_G          # P = 1*G
    n = 1
    start = time.perf_counter()
    last_print = start
    try:
        while True:
            if P == Q:
                print(f"WOW, found d = {n}. (This should be statistically impossible.)")
                return
            if n % every == 0:
                now = time.perf_counter()
                rate = n / (now - start)
                prob = n / total
                years = (total - n) / rate / 31_557_600
                print(random.choice(PUNS).format(n=n))
                if every > 1 or n % 1000 == 0:
                    print(f"    speed: {rate:,.0f} guesses/s | "
                          f"chance so far: {prob:.2e} | "
                          f"worst-case time left: {years:.2e} years")
                if every == 1:
                    time.sleep(0.05)  # so you can actually read the puns
            P = ec_add(P, SECP_G, SECP_P)   # next guess: (n+1)*G
            n += 1
    except KeyboardInterrupt:
        elapsed = time.perf_counter() - start
        print(f"\nStopped after {n:,} guesses in {elapsed:.1f}s.")
        print(f"Fraction of key space covered: {n / total:.3e}")
        print(f"Universe age is about 4.4e17 s. Required guesses: ~2^256 = {total:.2e}.")
        print("Even Pollard's rho (~2^128 steps) is out of reach classically.")
        print("Shor's algorithm does it in polynomial time. That's the article.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--every", type=int, default=20000,
                    help="print a pun every N guesses (use 1 for every guess)")
    ap.add_argument("--skip-loop", action="store_true")
    args = ap.parse_args()

    Q = act1()
    act2()
    if not args.skip_loop:
        act3(Q, max(1, args.every))


if __name__ == "__main__":
    main()
