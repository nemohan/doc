# CPU



~~~c
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

void *worker(void *data){
        int i = 0;
        for(;;){
                i++;
        }
}

int main(int argc, char *argv[]){
        pthread_t tid[3];
        for ( int i = 0; i < 3; i++){
                pthread_create(&tid[i], NULL, worker, NULL);
        }
        pthread_join(tid[0], NULL);

}
~~~

