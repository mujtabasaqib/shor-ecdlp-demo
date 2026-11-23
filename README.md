# shor-ecdlp-demo

A small Python demo of why the elliptic curve discrete logarithm problem (ECDLP) behind Bitcoin and Ethereum keys is safe from classical computers but not from Shor's algorithm on a large quantum computer.

> The "quantum" part is a NumPy simulation on a tiny curve and cannot break any real key.

## What it does

Bitcoin and Ethereum use ECDSA on secp256k1: `Q = d·G`, where `d` is the private key and `Q` the public key.

1. **Easy direction:** computes `Q = d·G` on real secp256k1 instantly.
2. **Toy Shor:** simulates the quantum circuit on a tiny curve and recovers `d` using the QFT and a modular inverse. The simulation needs n² memory, so it can't scale.
3. **Brute force:** guesses `d = 1, 2, 3, ...` against a real public key in an endless loop, showing the odds and time left. Stop with `Ctrl+C`.

## Usage

```bash
pip install numpy
python shor_ecdlp_demo.py                # all acts
python shor_ecdlp_demo.py --every 1      # runs every guess
python shor_ecdlp_demo.py --skip-loop    # skip the endless loop
```

## Related sources

- [BIP 361: Post Quantum Migration and Legacy Signature Sunset](https://bitcoin.org/bip/361/)
- [SHRINCS: compact hash-based signatures (draft)](https://github.com/SHRINCS/shrincs-bip/blob/main/SHRINCS.md)
- [Post-quantum cryptography on Ethereum](https://ethereum.org/roadmap/security/quantum-resistance/)

