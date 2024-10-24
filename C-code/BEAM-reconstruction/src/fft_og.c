#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define M_PI 3.1415926535897932384

// Definición explícita de la unidad imaginaria
#ifdef __GNUC__
#define COMPLEX_I (__extension__ 1.0iF)
#else
#define COMPLEX_I _Complex_I
#endif

// Definición del tipo complejo
typedef double _Complex complex_double;

// Funciones auxiliares para números complejos
complex_double make_complex(double real, double imag) {
    return real + COMPLEX_I * imag;
}

complex_double complex_add(complex_double a, complex_double b) {
    return a + b;
}

complex_double complex_sub(complex_double a, complex_double b) {
    return a - b;
}

complex_double complex_mul(complex_double a, complex_double b) {
    return a * b;
}

complex_double complex_exp(double theta) {
    return cos(theta) + COMPLEX_I * sin(theta);
}

double complex_real(complex_double z) {
    return __real__ z;
}

double complex_imag(complex_double z) {
    return __imag__ z;
}

int int_log2(int N) {
    int k = N, i = 0;
    while(k) {
        k >>= 1;
        i++;
    }
    return i - 1;
}

int check(int n) {
    return n > 0 && (n & (n - 1)) == 0;
}

int reverse(int N, int n) {
    int j, p = 0;
    for(j = 1; j <= int_log2(N); j++) {
        if(n & (1 << (int_log2(N) - j)))
            p |= 1 << (j - 1);
    }
    return p;
}

void ordina(complex_double* f1, int N) {
    complex_double* f2 = (complex_double*)malloc(N * sizeof(complex_double));
    for(int i = 0; i < N; i++)
        f2[i] = f1[reverse(N, i)];
    for(int j = 0; j < N; j++)
        f1[j] = f2[j];
    free(f2); // Liberamos la memoria dinámica
}

void transform(complex_double* f, int N) {
    ordina(f, N);
    complex_double* W = (complex_double*)malloc(N / 2 * sizeof(complex_double));
    
    // Calcular las raíces de la unidad
    for(int i = 0; i < N / 2; i++)
        W[i] = complex_exp(-2.0 * M_PI * i / N);
    
    int n = 1;
    int a = N / 2;
    for(int j = 0; j < int_log2(N); j++) {
        for(int i = 0; i < N; i++) {
            if(!(i & n)) {
                complex_double temp = f[i];
                complex_double Temp = complex_mul(W[(i * a) % (n * a)], f[i + n]);
                f[i] = complex_add(temp, Temp);
                f[i + n] = complex_sub(temp, Temp);
            }
        }
        n *= 2;
        a = a / 2;
    }
    free(W); // Liberamos la memoria dinámica
}

void FFT(complex_double* f, int N, double d) {
    transform(f, N);
    for(int i = 0; i < N; i++)
        f[i] *= d;
}

int main() {
    int n;
    do {
        printf("Especifique la dimensión del array (DEBE ser potencia de 2):\n");
        scanf("%d", &n);
    } while(!check(n));
    
    double d;
    printf("Especifique el paso de muestreo:\n");
    scanf("%lf", &d);
    
    // Asignación dinámica del array complejo basado en el valor de n
    complex_double* vec = (complex_double*)malloc(n * sizeof(complex_double));
    
    printf("Especifique el array:\n");
    for(int i = 0; i < n; i++) {
        double real, imag;
        printf("Especifique el elemento número %d (parte real y parte imaginaria):\n", i);
        if (scanf("%lf %lf", &real, &imag) != 2) {
            printf("Entrada inválida. Por favor, introduzca números válidos.\n");
            i--; // Volver a pedir la entrada si es inválida
            continue;
        }
        vec[i] = make_complex(real, imag);
    }
    
    FFT(vec, n, d);
    
    printf("... Imprimiendo la FFT del array especificado:\n");
    for(int j = 0; j < n; j++) {
        if(complex_imag(vec[j]) < 0)
            printf("%.2f - %.2fi\n", complex_real(vec[j]), -complex_imag(vec[j]));
        else
            printf("%.2f + %.2fi\n", complex_real(vec[j]), complex_imag(vec[j]));
    }
    
    // Liberar la memoria asignada para el array vec
    free(vec);
    
    return 0;
}