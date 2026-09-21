<?php
include 'koneksi.php';

// Tangkap data yang dikirimkan dari form
$id = $_POST['id'];
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

if ($nama_file) {
    // Set path untuk menyimpan file di server
    $path = "plugins/img/" . $nama_file;

    // Pindahkan file yang di-upload ke direktori yang ditentukan
    if (move_uploaded_file($tmp_file, $path)) {
        // Query untuk mengupdate data buku dengan cover baru
        $sql = "UPDATE buku SET nama_buku = ?, sinopsis = ?, penulis = ?, penerbit = ?, tahun_terbit = ?, cover_buku = ? WHERE id = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param("ssssisi", $nama_buku, $sinopsis, $penulis, $penerbit, $terbit, $nama_file, $id);
    } else {
        echo "Error: Gagal mengupload cover buku.";
        exit;
    }
} else {
    // Query untuk mengupdate data buku tanpa cover baru
    $sql = "UPDATE buku SET nama_buku = ?, sinopsis = ?, penulis = ?, penerbit = ?, tahun_terbit = ? WHERE id = ?";
    $stmt = $conn->prepare($sql);
    $stmt->bind_param("ssssii", $nama_buku, $sinopsis, $penulis, $penerbit, $terbit, $id);
}

// Jalankan query
if ($stmt->execute()) {
    // Jika berhasil update buku, redirect ke halaman buku.php
    header("location: buku.php");
} else {
    // Jika gagal update buku, tampilkan pesan error
    echo "Error: " . $sql . "<br>" . $conn->error;
}

// Tutup statement dan koneksi database
$stmt->close();
$conn->close();
?>
