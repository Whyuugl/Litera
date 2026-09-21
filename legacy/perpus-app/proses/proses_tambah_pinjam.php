<?php
// Include file koneksi untuk menghubungkan ke database
include '../koneksi.php';

// Tangkap data yang dikirimkan dari form
$nama_peminjam = $_POST['nama_peminjam'];
$nama_buku = $_POST['nama_buku'];
$tanggal_peminjaman = $_POST['tanggal_peminjaman'];

// Handle file upload
$nama_file = $_FILES['foto_buku']['name'];
$ukuran_file = $_FILES['foto_buku']['size'];
$tipe_file = $_FILES['foto_buku']['type'];
$tmp_file = $_FILES['foto_buku']['tmp_name'];

// Set path untuk menyimpan file di server
$target_dir = "../uploads/"; // Sesuaikan dengan path di server Anda
$target_file = $target_dir . basename($_FILES["foto_buku"]["name"]);

// Memindahkan file yang diupload ke direktori yang ditentukan
if (move_uploaded_file($_FILES["foto_buku"]["tmp_name"], $target_file)) {
    // Query untuk menyimpan data peminjaman ke database
    $sql = "INSERT INTO peminjaman (nama_peminjam, nama_buku, tanggal_peminjaman, foto_buku) VALUES (?, ?, ?, ?)";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("ssss", $nama_peminjam, $nama_buku, $tanggal_peminjaman, $nama_file);

    if ($stmt->execute()) {
        // Jika berhasil tambahkan peminjaman dan upload gambar, redirect ke halaman peminjaman.php
        header("location: ../peminjaman.php");
    } else {
        // Jika gagal, tampilkan pesan error
        echo "Error: " . $sql . "<br>" . $conn->error;
    }

    // Tutup statement
    $stmt->close();
} else {
    echo "Maaf, terjadi kesalahan saat mengunggah file.";
}

// Tutup koneksi database
$conn->close();
?>
