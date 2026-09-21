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
                        <a class="nav-link" href="buku.php">Buku</a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="anggota.php">Anggota</a>
                    </li>
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown" aria-expanded="false">
                            Transaksi
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#">Peminjaman</a></li>
                            <li><a class="dropdown-item" href="#">Pengembalian</a></li>
                        </ul>
                    </li>
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
            <div class="py-5 text-center">
                <img class="d-block mx-auto mb-4" src="plugins/img/th.jpeg" alt="" width="72" height="57">
                <h2>From Tambah Buku</h2>
                <p class="lead">Below is an example form built entirely with Bootstrap’s form controls. Each required form group has a validation state that can be triggered by attempting to submit the form without completing it.</p>
            </div>
            <div class="col-md-7 col-lg-8">
                <form class="needs-validation" novalidate action="proses_tambah.php" method="post" enctype="multipart/form-data">
                    <div class="row g-3">
                        <div class="col-12">
                            <label for="cover_buku" class="form-label">Pilih Cover Buku</label>
                            <input class="form-control" type="file" id="cover_buku" name="cover_buku">
                        </div>

                        <div class="col-12">
                            <label for="nama_buku" class="form-label">Nama Buku</label>
                            <input type="text" class="form-control" id="nama_buku" name="nama_buku" placeholder="Nama Buku" value="" required>
                            <div class="invalid-feedback">
                                Masukkan Nama Buku.
                            </div>
                        </div>

                        <div class="col-12">
                            <label for="sinopsis" class="form-label">Sinopsis Buku</label>
                            <input type="textarea" class="form-control" id="sinopsis" name="sinopsis" placeholder="Masukkan Sinopsis Buku" value="" required>
                            <div class="invalid-feedback">
                                Masukkan Sinonsis Buku.
                            </div>
                        </div>

                        <div class="col-12">
                            <label for="penulis" class="form-label">Penulis</label>
                            <input type="text" class="form-control" id="penulis" name="penulis" placeholder="Masukkan Penulis" required>
                            <div class="invalid-feedback">
                                Masukkan Nama Penulis.
                            </div>
                        </div>

                        <div class="col-12">
                            <label for="penerbit" class="form-label">Penerbit</label>
                            <input type="text" class="form-control" id="penerbit" name="penerbit" placeholder="Masukkan Penerbit" required>
                            <div class="invalid-feedback">
                                Masukkan Nama Penerbit.
                            </div>
                        </div>

                        <div class="col-12">
                            <label for="terbit" class="form-label">Tahun Terbit</label>
                            <input type="text" class="form-control" id="terbit" name="terbit" placeholder="Masukkan Tahun terbit" value="" required>
                            <div class="invalid-feedback">
                                Masukkan Tahun Terbit.
                            </div>
                        </div>
                    </div>

                    <hr class="my-4">

                    <div class="btn-group d-flex justify-content-between align-items-center gap-4">
                        <button class="w-100 btn btn-primary btn-lg" type="submit">Simpan</button>
                        <button class="w-100 btn btn-warning btn-lg" type="submit">Batal</button>
                    </div>

                </form>
            </div>
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
        </main>
    </div>


    <!-- Script Boostrap -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
</body>

</html>