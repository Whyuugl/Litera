<?php
// Include file koneksi untuk menghubungkan ke database
include 'koneksi.php';

// Tangkap data yang dikirimkan dari form
$nama_buku = $_POST['nama_buku'];
$sinopsis = $_POST['sinopsis'];
$penulis = $_POST['penulis'];
$penerbit = $_POST['penerbit'];
$terbit = $_POST['terbit'];

// Handle file upload
$nama_file = $_FILES['cover_buku']['name'];
$ukuran_file = $_FILES['cover_buku']['size'];
$tipe_file = $_FILES['cover_buku']['type'];
$tmp_file = $_FILES['cover_buku']['tmp_name'];

// Set path untuk menyimpan file di server
$path = "plugins/img/" . $nama_file;

// Query untuk menambahkan buku baru ke dalam database
$sql = "INSERT INTO buku (nama_buku, sinopsis, penulis, penerbit, tahun_terbit, cover_buku) VALUES (?, ?, ?, ?, ?, ?)";
$stmt = $conn->prepare($sql);
$stmt->bind_param("ssssis", $nama_buku, $sinopsis, $penulis, $penerbit, $terbit, $nama_file);

// Handle file upload and execute query
if (move_uploaded_file($tmp_file, $path) && $stmt->execute()) {
    // Jika berhasil tambahkan buku dan upload gambar, redirect ke halaman buku.php
    header("location: buku.php");
} else {
    // Jika gagal, tampilkan pesan error
    echo "Error: " . $sql . "<br>" . $conn->error;
}

// Tutup statement dan koneksi database
$stmt->close();
$conn->close();
?>
