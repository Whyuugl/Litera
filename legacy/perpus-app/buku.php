<?php
include 'koneksi.php';

$search = ''; // Variabel untuk menyimpan kata kunci pencarian

// Memeriksa apakah terdapat parameter pencarian dalam URL
if (isset($_GET['search'])) {
    // Membersihkan dan menyimpan nilai pencarian
    $search = trim($_GET['search']);
    $search = mysqli_real_escape_string($conn, $search); // Melakukan escape string untuk mencegah SQL injection
}

// Query untuk mendapatkan data buku berdasarkan pencarian
$sql = "SELECT id, cover_buku, nama_buku, penulis, penerbit, tahun_terbit, sinopsis FROM buku";
if (!empty($search)) {
    $sql .= " WHERE nama_buku LIKE '%$search%'";
}

// Eksekusi query
$result = $conn->query($sql);

// Memeriksa apakah terdapat hasil dari query
$listBuku = [];
if ($result && $result->num_rows > 0) {
    $listBuku = $result->fetch_all(MYSQLI_ASSOC);
}

// Menentukan apakah tombol Back harus ditampilkan
$showBackButton = !empty($search);
?>

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
            <img class="navbar-brand" src="plugins/img/th.jpeg" style="width: 80px;"></img>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent" aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarSupportedContent">
                <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                    <li class="nav-item">
                        <a class="nav-link" aria-current="page" href="index.php">Beranda</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link active" href="buku.php">Buku</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="anggota.php">Anggota</a>
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
                <form class="d-flex" method="GET" action="buku.php">
                    <?php if ($showBackButton) : ?>
                        <a href="buku.php" class="btn btn-outline-secondary me-2">Back</a>
                    <?php else : ?>
                        <input class="form-control me-2" type="search" placeholder="Search" aria-label="Search" name="search" value="<?= htmlentities($search) ?>">
                        <button class="btn btn-outline-success" type="submit">Search</button>
                    <?php endif; ?>
                </form>
            </div>
        </div>
    </nav>

    <div class="container">
        <main>
            <div class="container py-5">
                <div class="p-3 bg-body-tertiary rounded-3">
                    <div class="container-fluid">
                        <h1 class="display-6 fw-bold">Daftar Buku</h1>
                        <button class="btn btn-primary btn-lg mt-3" type="button"><a href="formbuku.php" style="text-decoration: none; color:white;">Tambah Buku</a></button>
                    </div>
                </div>

                <!-- Koleksi Buku -->
                <div class="album py-5 bg-body-tertiary">
                    <div class="container">
                        <div class="row row-cols-1 row-cols-sm-2 row-cols-md-3 g-1">
                            <?php if (!empty($listBuku)) : ?>
                                <?php foreach ($listBuku as $buku) : ?>
                                    <div class="col g-3">
                                        <div class="card shadow-sm">
                                            <a href="detail.php?id=<?= $buku['id'] ?>" style="text-decoration: none; color: inherit;">
                                                <img class="bd-placeholder-img card-img-top" width="100%" height="300" src="plugins/img/<?= $buku['cover_buku'] ?>" role="img" aria-label="Placeholder: Thumbnail" preserveAspectRatio="xMidYMid slice" focusable="false"></img>
                                                <div class="card-body">
                                                    <p class="card-text fw-bold"><?= $buku['nama_buku'] ?> <br>Ditulis Oleh <?= $buku['penulis'] ?></p>
                                                    <p class="card-text"><?= substr($buku['sinopsis'], 0, 150) . "..." ?></p>
                                                    <div class="d-flex justify-content-between align-items-center">
                                                        <div class="btn-group">
                                                        <a href="edit.php?id=<?= $buku['id'] ?>" class="btn btn-sm btn-outline-secondary">Edit</a>
                                                            <form action="proses_delete.php" method="post" onsubmit="return confirm('Apakah Anda yakin ingin menghapus buku ini?')">
                                                                <input type="hidden" name="id" value="<?= $buku['id'] ?>">
                                                                <button type="submit" class="btn btn-sm btn-outline-secondary">Delete</button>
                                                            </form>
                                                        </div>
                                                        <small class="text-body-secondary"><?= $buku['tahun_terbit'] ?></small>
                                                        <small class="text-body-secondary">Oleh <?= $buku['penerbit'] ?></small>
                                                    </div>
                                                </div>
                                            </a>
                                        </div>
                                    </div>
                                <?php endforeach ?>
                            <?php else : ?>
                                <div class="col">
                                    <div class="card shadow-sm">
                                        <div class="card-body text-center">
                                            <p class="card-text">Tidak ada buku yang sesuai dengan pencarian Anda.</p>
                                        </div>
                                    </div>
                                </div>
                            <?php endif; ?>
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
