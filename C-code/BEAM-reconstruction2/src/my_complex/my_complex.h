#ifndef MY_COMPLEX
#define MY_COMPLEX

#include <stdint.h>
#include <stdlib.h>

typedef struct {
    double real;
    double imag;
} Complex;

/**
 * @brief Realiza la multiplicación de dos números complejos.
 * @param a Primer número complejo.
 * @param b Segundo número complejo.
 * @return Resultado de la multiplicación.
 */
Complex complex_mult(Complex a, Complex b);

/**
 * @brief Realiza la suma de dos números complejos.
 * @param a Primer número complejo.
 * @param b Segundo número complejo.
 * @return Resultado de la suma.
 */
Complex complex_add(Complex a, Complex b);

/**
 * @brief Realiza la resta de dos números complejos.
 * @param a Primer número complejo.
 * @param b Segundo número complejo.
 * @return Resultado de la resta.
 */
Complex complex_sub(Complex a, Complex b);

/**
 * @brief Convierte vectores I y Q en un vector de números complejos.
 * @param I Puntero a los datos I.
 * @param Q Puntero a los datos Q.
 * @param N Número de elementos en los vectores I y Q.
 * @return Puntero al vector de números complejos.
 */
Complex* convert_to_complex(const uint8_t* I, const uint8_t* Q, size_t N);


double complex_magnitude(Complex c);


Complex* convert_to_complex(const uint8_t* I, const uint8_t* Q, size_t N);

#endif
