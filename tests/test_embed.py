import pytest
from watermark.metrics import calculate_ber, calculate_nc

def test_ber_identical():
    """Uji Bit Error Rate jika bit identik (harus 0.0)"""
    assert calculate_ber("10101010", "10101010") == 0.0

def test_ber_different():
    """Uji Bit Error Rate jika ada 1 bit berbeda dari 8 bit (1/8 = 0.125)"""
    assert calculate_ber("10101010", "10101000") == 0.125

def test_nc_identical():
    """Uji Normalized Correlation jika bit identik (menggunakan pytest.approx karena float)"""
    assert calculate_nc("1010", "1010") == pytest.approx(1.0)

def test_nc_empty():
    """Uji Normalized Correlation jika data kosong"""
    assert calculate_nc("", "") == 0.0

def test_ber_empty():
    """Uji Bit Error Rate jika data kosong"""
    assert calculate_ber("", "") == 1.0