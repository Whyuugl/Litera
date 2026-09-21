<?php
// Memeriksa apakah request merupakan POST
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Memeriksa apakah data yang diperlukan telah diterima dari form
    if (isset($_POST['id'], $_POST['nama_peminjam'], $_POST['nama_buku'], $_POST['tanggal_peminjaman'])) {
        $id = $_POST['id'];
        $nama_peminjam = $_POST['nama_peminjam'];
        $nama_buku = $_POST['nama_buku'];
        $tanggal_peminjaman = $_POST['tanggal_peminjaman'];
        $existing_foto_buku = $_POST['existing_foto_buku'];

        // Memeriksa apakah ada file foto buku yang diupload
        if (isset($_FILES['foto_buku']) && $_FILES['foto_buku']['error'] == UPLOAD_ERR_OK) {
            $foto_buku = $_FILES['foto_buku'];
            $foto_buku_name = time() . '-' . $foto_buku['name'];
            $foto_buku_tmp_name = $foto_buku['tmp_name'];
            $foto_buku_size = $foto_buku['size'];
            $foto_buku_error = $foto_buku['error'];

            // Memindahkan file yang diupload ke direktori tujuan
            $upload_dir = '../uploads/';
            $upload_file = $upload_dir . basename($foto_buku_name);
            if (move_uploaded_file($foto_buku_tmp_name, $upload_file)) {
                $uploaded_foto_buku = $foto_buku_name;
            } else {
                echo "Gagal mengupload file.";
                exit;
            }
        } else {
            $uploaded_foto_buku = $existing_foto_buku;
        }

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

        // Query untuk update data peminjaman
        $sql = "UPDATE peminjaman SET nama_peminjam = ?, nama_buku = ?, tanggal_peminjaman = ?, foto_buku = ? WHERE id = ?";
        $stmt = $conn->prepare($sql);
        $stmt->bind_param("ssssi", $nama_peminjam, $nama_buku, $tanggal_peminjaman, $uploaded_foto_buku, $id);

        // Menjalankan query
        if ($stmt->execute()) {
            echo "<script>alert('Data peminjaman berhasil diubah.'); window.location.href = '../peminjaman.php';</script>";
        } else {
            echo "Gagal mengubah data peminjaman: " . $stmt->error;
        }

        // Menutup statement dan koneksi
        $stmt->close();
        $conn->close();
    } else {
        echo "<script>alert('Data yang diperlukan tidak lengkap.'); window.location.href = '../edit_peminjam.php?id=$id';</script>";
    }
} else {
    echo "<script>alert('Metode request tidak valid.'); window.location.href = '../peminjaman.php';</script>";
}
?>
