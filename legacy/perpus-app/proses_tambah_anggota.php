<?php
// Konfigurasi database
$host = 'localhost';  // Ganti dengan host database Anda
$username = 'root';   // Ganti dengan username database Anda
$password = '';       // Ganti dengan password database Anda
$dbname = 'db_perpus'; // Ganti dengan nama database Anda

// Membuat koneksi ke database
$conn = new mysqli($host, $username, $password, $dbname);

// Memeriksa koneksi
if ($conn->connect_error) {
    die("Koneksi gagal: " . $conn->connect_error);
}

// Mengambil data dari formulir tambah anggota
$nama = $_POST['nama'];
$umur = $_POST['umur'];
$alamat = $_POST['alamat'];
$no_hp = $_POST['no_hp'];

// Query untuk menyimpan data anggota ke database
$sql = "INSERT INTO anggota (nama, umur, alamat, no_hp) VALUES ('$nama', '$umur', '$alamat', '$no_hp')";

if ($conn->query($sql) === TRUE) {
    // Jika berhasil disimpan, kembali ke halaman anggota.php
    header("Location: anggota.php");
    exit();
} else {
    echo "Error: " . $sql . "<br>" . $conn->error;
}

// Menutup koneksi
$conn->close();
?>
