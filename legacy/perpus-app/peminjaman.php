<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <title>Perpustakaan UMUM</title>
</head>
<body>
    <nav class="navbar navbar-expand-lg bg-body-tertiary">
        <div class="container-fluid">
            <img class="navbar-brand" src="plugins/img/th.jpeg" style="width: 80px;">
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarSupportedContent">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item">
                        <a class="nav-link" aria-current="page" href="index.php">Beranda</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="buku.php">Buku</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="anggota.php">Anggota</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            Transaksi
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="peminjaman.php">Peminjaman</a></li>
                            <li><a class="dropdown-item" href="#">Pengembalian</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        <main>
            <div class="container py-5">
                <div class="p-3 bg-body-tertiary rounded-3">
                    <div class="container-fluid">
                        <h1 class="display-6 fw-bold">Daftar Peminjaman Buku Perpustakaan</h1>
                        <button class="btn btn-primary btn-lg mt-3" type="button" onclick="window.location.href='form_tambah/formpeminjam.php'">Tambah Peminjaman</button>
                    </div>
                </div>

                <!-- Table Peminjaman Buku -->
                <div class="album py-5 bg-body-tertiary">
                    <div class="container">
                        <div class="table-responsive small">
                            <table class="table table-striped table-sm">
                                <thead>
                                    <tr>
                                        <th scope="col">No</th>
                                        <th scope="col">Nama Peminjam</th>
                                        <th scope="col">Nama Buku</th>
                                        <th scope="col">Tanggal Peminjaman</th>
                                        <th scope="col">Sampul Buku</th>
                                        <th scope="col">Aksi</th>
                                    </tr>
                                </thead>
                                <tbody>
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

                                    // Query untuk mengambil data peminjaman buku
                                    $sql = "SELECT * FROM peminjaman";
                                    $result = $conn->query($sql);

                                    // Memeriksa apakah ada hasil
                                    if ($result->num_rows > 0) {
                                        // Menampilkan data setiap baris
                                        $no = 1;
                                        while ($row = $result->fetch_assoc()) {
                                            echo "<tr>
                                                <td>" . $no . "</td>
                                                <td>" . $row['nama_peminjam'] . "</td>
                                                <td>" . $row['nama_buku'] . "</td>
                                                <td>" . $row['tanggal_peminjaman'] . "</td>
                                                <td><img src='uploads/" . $row['foto_buku'] . "' style='width: 100px; height: auto;' alt='Cover'></td>
                                                <td>
                                                    <form action='proses/proses_delete_pinjam.php' method='post'>
                                                        <a href='form_tambah/edit_peminjam.php?id=" . $row['id'] . "' class='btn btn-warning btn-sm'>Edit</a>
                                                        <input type='hidden' name='id' value='" . $row['id'] . "'>
                                                        <button type='submit' class='btn btn-danger btn-sm' onclick=\"return confirm('Anda yakin ingin menghapus data ini?')\">Delete</button>
                                                    </form>
                                                    <form action='proses/proses_pengembalian.php' method='post'>
                                                        <input type='hidden' name='id' value='" . $row['id'] . "'>
                                                        <button type='submit' class='btn btn-success btn-sm' onclick=\"return confirm('Anda yakin ingin mengembalikan buku ini?')\">Pengembalian</button>
                                                    </form>
                                                </td>
                                            </tr>";
                                            $no++;
                                        }
                                    } else {
                                        echo "<tr><td colspan='6' class='text-center'>Tidak ada data peminjaman buku</td></tr>";
                                    }

                                    // Menutup koneksi
                                    $conn->close();
                                    ?>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- Footer -->
                <footer class="d-flex flex-wrap justify-content-between align-items-center py-3 my-4 border-top">
                    <p class="col-md-4 mb-0 text-body-secondary">&copy; 2024 Company, Inc</p>

                    <a href="/" class="col-md-4 d-flex align-items-center justify-content-center mb-3 mb-md-0 me-md-auto link-body-emphasis text-decoration-none">
                        <svg class="bi me-2" width="40" height="32">
                            <use xlink:href="#bootstrap" />
                        </svg>
                    </a>

                    <ul class="nav col-md-4 justify-content-end">
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">Home</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">Features</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">Pricing</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">FAQs</a></li>
                        <li class="nav-item"><a href="#" class="nav-link px-2 text-body-secondary">About</a></li>
                    </ul>
                </footer>
            </div>
        </main>
    </div>

    <!-- Script Boostrap -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
</body>
</html>
